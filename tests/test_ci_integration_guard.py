import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFTEST_PATH = REPO_ROOT / "conftest.py"
CI_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"
COMPOSE_PATH = REPO_ROOT / "deployments" / "docker-compose.yml"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"


def _run_isolated_pytest(
    tmp_path: Path,
    test_source: str,
    *,
    extra_env: dict[str, str] | None = None,
    pytest_args: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    assert CONFTEST_PATH.exists(), "conftest.py na raiz do repositório não encontrado"

    (tmp_path / "conftest.py").write_text(
        CONFTEST_PATH.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\n'
        'markers = ["integration: integration tests"]\n',
        encoding="utf-8",
    )
    test_file = tmp_path / "test_sample.py"
    test_file.write_text(test_source, encoding="utf-8")

    env = os.environ.copy()
    env.pop("CI_REQUIRE_INTEGRATION", None)
    if extra_env:
        env.update(extra_env)

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-v",
        *(pytest_args or []),
        str(test_file),
    ]
    return subprocess.run(
        cmd,
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


def test_integration_skipif_is_allowed_by_default(tmp_path: Path):
    result = _run_isolated_pytest(
        tmp_path,
        """
import pytest

@pytest.mark.integration
@pytest.mark.skipif(True, reason="infra indisponível")
def test_skipped_integration():
    assert True
""",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 skipped" in result.stdout


def test_integration_skipif_fails_when_ci_require_integration_enabled(tmp_path: Path):
    result = _run_isolated_pytest(
        tmp_path,
        """
import pytest

@pytest.mark.integration
@pytest.mark.skipif(True, reason="broker offline")
def test_skipped_integration():
    assert True
""",
        extra_env={"CI_REQUIRE_INTEGRATION": "1"},
        pytest_args=["-m", "integration"],
    )

    assert result.returncode != 0
    assert "skipped" not in result.stdout.splitlines()[-1]
    assert "CI_REQUIRE_INTEGRATION" in result.stdout
    assert "broker offline" in result.stdout


def test_integration_runtime_skip_fails_when_ci_require_integration_enabled(
    tmp_path: Path,
):
    result = _run_isolated_pytest(
        tmp_path,
        """
import pytest

@pytest.mark.integration
def test_runtime_skip():
    pytest.skip("db não respondeu")
""",
        extra_env={"CI_REQUIRE_INTEGRATION": "1"},
        pytest_args=["-m", "integration"],
    )

    assert result.returncode != 0
    assert "skipped" not in result.stdout.splitlines()[-1]
    assert "db não respondeu" in result.stdout


def test_module_level_skip_fails_when_ci_require_integration_enabled(tmp_path: Path):
    result = _run_isolated_pytest(
        tmp_path,
        """
import pytest

pytest.skip("módulo inteiro indisponível", allow_module_level=True)

@pytest.mark.integration
def test_never_collected():
    assert True
""",
        extra_env={"CI_REQUIRE_INTEGRATION": "1"},
        pytest_args=["-m", "integration"],
    )

    assert result.returncode != 0
    assert "módulo inteiro indisponível" in result.stdout


def test_non_integration_skip_remains_skipped_when_ci_require_integration_enabled(
    tmp_path: Path,
):
    result = _run_isolated_pytest(
        tmp_path,
        """
import pytest

@pytest.mark.skipif(True, reason="apenas windows")
def test_unit_skipped():
    assert True
""",
        extra_env={"CI_REQUIRE_INTEGRATION": "1"},
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 skipped" in result.stdout


def test_passing_integration_test_passes_with_ci_require_integration_enabled(
    tmp_path: Path,
):
    result = _run_isolated_pytest(
        tmp_path,
        """
import pytest

@pytest.mark.integration
def test_healthy_integration():
    assert 1 + 1 == 2
""",
        extra_env={"CI_REQUIRE_INTEGRATION": "1"},
        pytest_args=["-m", "integration"],
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 passed" in result.stdout


def test_integration_fixture_skip_fails_when_ci_require_integration_enabled(
    tmp_path: Path,
):
    result = _run_isolated_pytest(
        tmp_path,
        """
import pytest

@pytest.fixture
def unavailable_service():
    pytest.skip("fixture sem conexão com o banco")

@pytest.mark.integration
def test_uses_fixture(unavailable_service):
    assert True
""",
        extra_env={"CI_REQUIRE_INTEGRATION": "1"},
        pytest_args=["-m", "integration"],
    )

    assert result.returncode != 0
    assert "skipped" not in result.stdout.splitlines()[-1]
    assert "CI_REQUIRE_INTEGRATION" in result.stdout
    assert "fixture sem conexão com o banco" in result.stdout


def test_integration_real_assertion_failure_is_preserved(tmp_path: Path):
    result = _run_isolated_pytest(
        tmp_path,
        """
import pytest

@pytest.mark.integration
def test_real_failure():
    assert False, "erro real de contrato"
""",
        extra_env={"CI_REQUIRE_INTEGRATION": "1"},
        pytest_args=["-m", "integration"],
    )

    assert result.returncode != 0
    assert "erro real de contrato" in result.stdout
    assert "Teste de integração pulado com CI_REQUIRE_INTEGRATION=1" not in result.stdout


@pytest.mark.parametrize("env_value", ["0", "false", "no", ""])
def test_falsy_ci_require_integration_values_allow_skip(
    tmp_path: Path, env_value: str
):
    result = _run_isolated_pytest(
        tmp_path,
        """
import pytest

@pytest.mark.integration
@pytest.mark.skipif(True, reason="infra desligada localmente")
def test_local_skip():
    assert True
""",
        extra_env={"CI_REQUIRE_INTEGRATION": env_value},
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 skipped" in result.stdout


def test_integration_xfail_is_not_converted_to_forbidden_skip(tmp_path: Path):
    result = _run_isolated_pytest(
        tmp_path,
        """
import pytest

@pytest.mark.integration
@pytest.mark.xfail(reason="falha esperada conhecida")
def test_expected_failure():
    assert False
""",
        extra_env={"CI_REQUIRE_INTEGRATION": "1"},
        pytest_args=["-m", "integration"],
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 xfailed" in result.stdout


def test_zero_integration_tests_collected_exits_nonzero(tmp_path: Path):
    result = _run_isolated_pytest(
        tmp_path,
        """
def test_only_unit():
    assert True
""",
        extra_env={"CI_REQUIRE_INTEGRATION": "1"},
        pytest_args=["-m", "integration"],
    )

    assert result.returncode == int(pytest.ExitCode.NO_TESTS_COLLECTED)


def test_ci_workflow_defines_dedicated_integration_job():
    workflow = CI_WORKFLOW_PATH.read_text(encoding="utf-8")

    assert re.search(r"^\s{2}test-integration:\s*$", workflow, re.MULTILINE)
    assert 'uv run pytest -m "not integration"' in workflow
    assert "docker compose -f deployments/docker-compose.yml up -d --build --wait" in workflow
    assert "CI_REQUIRE_INTEGRATION" in workflow
    assert "uv run pytest -m integration -v" in workflow
    assert "if: failure()" in workflow
    assert "docker compose -f deployments/docker-compose.yml logs" in workflow
    assert "if: always()" in workflow
    assert "docker compose -f deployments/docker-compose.yml down -v" in workflow


def test_docker_compose_defines_healthchecks_for_integration_services():
    compose = COMPOSE_PATH.read_text(encoding="utf-8")

    for service in ("db", "broker", "gateway", "nginx"):
        match = re.search(
            rf"^\s{{2}}{service}:\n(.*?)(?=^\s{{2}}[a-z0-9_-]+:|\Z)",
            compose,
            re.MULTILINE | re.DOTALL,
        )
        assert match is not None, f"Serviço '{service}' ausente no docker-compose.yml"
        assert "healthcheck:" in match.group(1), (
            f"Serviço '{service}' precisa de healthcheck para suporte a --wait"
        )


def test_pyproject_integration_marker_describes_all_services():
    data = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
    markers = data["tool"]["pytest"]["ini_options"]["markers"]
    integration_markers = [m for m in markers if m.startswith("integration:")]

    assert len(integration_markers) == 1
    description = integration_markers[0].lower()
    assert "mqtt" in description
    assert "timescaledb" in description
