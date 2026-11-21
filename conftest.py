import os

import pytest

_TRUTHY_VALUES = {"1", "true", "yes", "on"}


def _is_integration_required() -> bool:
    return os.getenv("CI_REQUIRE_INTEGRATION", "").strip().lower() in _TRUTHY_VALUES


def _extract_skip_reason(report: pytest.TestReport | pytest.CollectReport) -> str:
    longrepr = report.longrepr
    if isinstance(longrepr, tuple) and len(longrepr) >= 3:
        return str(longrepr[2]).removeprefix("Skipped: ")
    return str(longrepr or "motivo não informado")


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[object]):
    report = yield
    if (
        _is_integration_required()
        and item.get_closest_marker("integration") is not None
        and report.skipped
        and not getattr(report, "wasxfail", None)
    ):
        reason = _extract_skip_reason(report)
        report.outcome = "failed"
        report.longrepr = (
            "Teste de integração pulado com CI_REQUIRE_INTEGRATION=1: "
            f"{reason}"
        )
    return report


@pytest.hookimpl(wrapper=True)
def pytest_make_collect_report(collector: pytest.Collector):
    report = yield
    if _is_integration_required() and report.skipped:
        reason = _extract_skip_reason(report)
        report.outcome = "failed"
        report.longrepr = (
            "Módulo pulado na coleta com CI_REQUIRE_INTEGRATION=1: "
            f"{reason}"
        )
    return report
