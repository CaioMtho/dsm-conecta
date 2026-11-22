import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCKER_DIR = REPO_ROOT / "deployments" / "docker"
INIT_TIMESCALEDB_SQL = DOCKER_DIR / "init-timescaledb.sql"
AGGREGATES_SQL = DOCKER_DIR / "init-aggregates.sql"
RELATIONAL_SQL = DOCKER_DIR / "init-relational.sql"
COMPOSE_FILE = REPO_ROOT / "deployments" / "docker-compose.yml"
DEPLOY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deploy.yml"

DB_CONTAINER = os.getenv("DB_CONTAINER", "dsm_db")
PSQL = (
    'psql -X -q -t -A -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
)

EXPECTED_AGGREGATE_COLUMNS = [
    "bucket",
    "category",
    "source",
    "screen_name",
    "event_ref_id",
    "quiz_profile",
    "event_count",
    "visitor_count_sum",
    "avg_duration_seconds",
]

EXPECTED_RELATIONAL_TABLES: dict[str, list[str]] = {
    "admin_users": [
        "id|uuid|NO",
        "email|character varying|NO",
        "name|character varying|NO",
        "password_hash|text|NO",
        "role|character varying|NO",
        "is_active|boolean|NO",
        "created_at|timestamp with time zone|NO",
        "updated_at|timestamp with time zone|NO",
    ],
    "course_info": [
        "id|uuid|NO",
        "slug|character varying|NO",
        "title|character varying|NO",
        "summary|text|NO",
        "graduate_profile|text|NO",
        "duration_semesters|smallint|NO",
        "shifts|jsonb|NO",
        "admission_forms|jsonb|NO",
        "status|character varying|NO",
        "created_by|uuid|YES",
        "approved_by|uuid|YES",
        "approved_at|timestamp with time zone|YES",
        "created_at|timestamp with time zone|NO",
        "updated_at|timestamp with time zone|NO",
    ],
    "curriculum_subjects": [
        "id|uuid|NO",
        "code|character varying|NO",
        "name|character varying|NO",
        "semester|smallint|NO",
        "workload_hours|smallint|NO",
        "description|text|NO",
        "status|character varying|NO",
        "created_by|uuid|YES",
        "approved_by|uuid|YES",
        "approved_at|timestamp with time zone|YES",
        "created_at|timestamp with time zone|NO",
        "updated_at|timestamp with time zone|NO",
    ],
    "projects": [
        "id|uuid|NO",
        "title|character varying|NO",
        "summary|character varying|NO",
        "description|text|NO",
        "image_url|text|YES",
        "technologies|jsonb|NO",
        "semester_label|character varying|NO",
        "authors|jsonb|NO",
        "repository_url|text|YES",
        "status|character varying|NO",
        "created_by|uuid|YES",
        "approved_by|uuid|YES",
        "approved_at|timestamp with time zone|YES",
        "created_at|timestamp with time zone|NO",
        "updated_at|timestamp with time zone|NO",
    ],
    "testimonials": [
        "id|uuid|NO",
        "author_name|character varying|NO",
        "author_role|character varying|NO",
        "graduation_year|smallint|YES",
        "quote|text|NO",
        "photo_url|text|YES",
        "status|character varying|NO",
        "created_by|uuid|YES",
        "approved_by|uuid|YES",
        "approved_at|timestamp with time zone|YES",
        "created_at|timestamp with time zone|NO",
        "updated_at|timestamp with time zone|NO",
    ],
    "events": [
        "id|uuid|NO",
        "title|character varying|NO",
        "description|text|NO",
        "event_type|character varying|NO",
        "location_name|character varying|NO",
        "latitude|double precision|YES",
        "longitude|double precision|YES",
        "starts_at|timestamp with time zone|NO",
        "ends_at|timestamp with time zone|NO",
        "qr_token|character varying|NO",
        "status|character varying|NO",
        "created_by|uuid|YES",
        "approved_by|uuid|YES",
        "approved_at|timestamp with time zone|YES",
        "created_at|timestamp with time zone|NO",
        "updated_at|timestamp with time zone|NO",
    ],
    "faqs": [
        "id|uuid|NO",
        "question|character varying|NO",
        "answer|text|NO",
        "display_order|integer|NO",
        "status|character varying|NO",
        "created_by|uuid|YES",
        "approved_by|uuid|YES",
        "approved_at|timestamp with time zone|YES",
        "created_at|timestamp with time zone|NO",
        "updated_at|timestamp with time zone|NO",
    ],
    "quiz_questions": [
        "id|uuid|NO",
        "prompt|text|NO",
        "display_order|integer|NO",
        "status|character varying|NO",
        "created_by|uuid|YES",
        "approved_by|uuid|YES",
        "approved_at|timestamp with time zone|YES",
        "created_at|timestamp with time zone|NO",
        "updated_at|timestamp with time zone|NO",
    ],
    "quiz_options": [
        "id|uuid|NO",
        "question_id|uuid|NO",
        "label|character varying|NO",
        "display_order|integer|NO",
        "weight_frontend_mobile|smallint|NO",
        "weight_backend_dados|smallint|NO",
        "weight_infra_iot|smallint|NO",
        "weight_fullstack|smallint|NO",
    ],
    "contact_messages": [
        "id|uuid|NO",
        "session_id|uuid|YES",
        "sender_name|character varying|YES",
        "sender_email|character varying|YES",
        "subject|character varying|NO",
        "message|text|NO",
        "is_resolved|boolean|NO",
        "resolved_by|uuid|YES",
        "resolved_at|timestamp with time zone|YES",
        "created_at|timestamp with time zone|NO",
    ],
    "event_checkins": [
        "id|uuid|NO",
        "event_id|uuid|NO",
        "session_id|uuid|NO",
        "method|character varying|NO",
        "latitude|double precision|YES",
        "longitude|double precision|YES",
        "distance_meters|double precision|YES",
        "checked_in_at|timestamp with time zone|NO",
    ],
    "quiz_submissions": [
        "id|uuid|NO",
        "session_id|uuid|NO",
        "answers|jsonb|NO",
        "scores|jsonb|NO",
        "percentages|jsonb|NO",
        "dominant_profile|character varying|NO",
        "submitted_at|timestamp with time zone|NO",
    ],
}

EXPECTED_INDEXES: dict[str, tuple[str, str]] = {
    "idx_curriculum_subjects_status_semester": (
        "curriculum_subjects",
        "status, semester, code",
    ),
    "idx_projects_status_created": ("projects", "status, created_at DESC"),
    "idx_testimonials_status_role": ("testimonials", "status, author_role"),
    "idx_events_status_starts": ("events", "status, starts_at"),
    "idx_faqs_status_order": ("faqs", "status, display_order"),
    "idx_quiz_questions_status_order": (
        "quiz_questions",
        "status, display_order",
    ),
    "idx_quiz_options_question_order": (
        "quiz_options",
        "question_id, display_order",
    ),
    "idx_event_checkins_session": (
        "event_checkins",
        "session_id, checked_in_at DESC",
    ),
    "idx_quiz_submissions_session": (
        "quiz_submissions",
        "session_id, submitted_at DESC",
    ),
    "idx_contact_messages_resolved": (
        "contact_messages",
        "is_resolved, created_at DESC",
    ),
}


def _sql_without_comments(path: Path) -> str:
    return re.sub(r"--[^\n]*", "", path.read_text(encoding="utf-8"))


def test_docker_compose_mounts_init_scripts_in_alphabetical_order():
    compose = COMPOSE_FILE.read_text(encoding="utf-8")
    expected_mounts = [
        (
            "./docker/init-timescaledb.sql:"
            "/docker-entrypoint-initdb.d/01-init-timescaledb.sql:ro"
        ),
        (
            "./docker/init-aggregates.sql:"
            "/docker-entrypoint-initdb.d/02-init-aggregates.sql:ro"
        ),
        (
            "./docker/init-relational.sql:"
            "/docker-entrypoint-initdb.d/03-init-relational.sql:ro"
        ),
    ]

    for mount in expected_mounts:
        assert mount in compose

    positions = [compose.index(mount) for mount in expected_mounts]
    assert positions == sorted(positions)


def test_deploy_workflow_copies_and_reapplies_all_init_scripts_in_order():
    workflow = DEPLOY_WORKFLOW.read_text(encoding="utf-8")
    source_match = re.search(r"source:\s*(.+)", workflow)
    assert source_match is not None
    source_line = source_match.group(1)

    for script in (
        "deployments/docker/init-timescaledb.sql",
        "deployments/docker/init-aggregates.sql",
        "deployments/docker/init-relational.sql",
    ):
        assert script in source_line

    applied = re.findall(
        r"psql[^\n]*-v\s+ON_ERROR_STOP=1[^\n]*<\s*(docker/init-[\w-]+\.sql)",
        workflow,
    )
    assert applied == [
        "docker/init-timescaledb.sql",
        "docker/init-aggregates.sql",
        "docker/init-relational.sql",
    ]


def test_aggregates_script_avoids_transaction_blocks_and_count_distinct():
    assert AGGREGATES_SQL.exists()
    sql = _sql_without_comments(AGGREGATES_SQL)

    assert not re.search(r"\bBEGIN\b", sql, re.IGNORECASE)
    assert not re.search(r"\bCOMMIT\b", sql, re.IGNORECASE)
    assert not re.search(r"\bDO\s*\$", sql, re.IGNORECASE)
    assert not re.search(r"\bCOUNT\s*\(\s*DISTINCT\b", sql, re.IGNORECASE)


def test_aggregates_script_is_idempotent():
    assert AGGREGATES_SQL.exists()
    sql = _sql_without_comments(AGGREGATES_SQL)

    unguarded_views = re.findall(
        r"\bCREATE\s+MATERIALIZED\s+VIEW\b(?!\s+IF\s+NOT\s+EXISTS)",
        sql,
        re.IGNORECASE,
    )
    assert unguarded_views == []

    views = re.findall(
        r"\bCREATE\s+MATERIALIZED\s+VIEW\s+IF\s+NOT\s+EXISTS\s+(\w+)(.*?);",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    views_by_name = dict(views)
    assert len(views) == 2
    assert set(views_by_name) == {"telemetry_hourly", "telemetry_daily"}

    expected_buckets = {
        "telemetry_hourly": r"INTERVAL\s+'1 hour'",
        "telemetry_daily": r"INTERVAL\s+'1 day'",
    }
    for name, bucket_pattern in expected_buckets.items():
        body = views_by_name[name]
        assert re.search(
            r"\bWITH\s*\([^)]*timescaledb\.continuous", body, re.IGNORECASE
        )
        assert re.search(r"\bWITH\s+NO\s+DATA\b", body, re.IGNORECASE)
        assert re.search(bucket_pattern, body, re.IGNORECASE)

    for function in ("add_continuous_aggregate_policy", "add_retention_policy"):
        calls = re.findall(
            rf"\b{function}\s*\((.*?)\)\s*;", sql, re.IGNORECASE | re.DOTALL
        )
        assert len(calls) == 2
        assert all(
            re.search(r"if_not_exists\s*=>\s*TRUE", call, re.IGNORECASE)
            for call in calls
        )


def test_relational_script_is_idempotent_and_declares_all_objects():
    assert RELATIONAL_SQL.exists()
    sql = _sql_without_comments(RELATIONAL_SQL)

    assert re.search(
        r"\bCREATE\s+EXTENSION\s+IF\s+NOT\s+EXISTS\s+pgcrypto\s*;",
        sql,
        re.IGNORECASE,
    )

    unguarded = re.findall(
        r"\bCREATE\s+(?:UNIQUE\s+)?(?:TABLE|INDEX|EXTENSION)\b"
        r"(?!\s+IF\s+NOT\s+EXISTS)",
        sql,
        re.IGNORECASE,
    )
    assert unguarded == []

    for table in EXPECTED_RELATIONAL_TABLES:
        assert re.search(
            rf"\bCREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+{table}\b",
            sql,
            re.IGNORECASE,
        )

    for index in EXPECTED_INDEXES:
        assert re.search(
            rf"\bCREATE\s+(?:UNIQUE\s+)?INDEX\s+IF\s+NOT\s+EXISTS\s+{index}\b",
            sql,
            re.IGNORECASE,
        )


def _is_db_ready() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        result = subprocess.run(
            ["docker", "exec", DB_CONTAINER, "pg_isready", "-q"],
            capture_output=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _psql(sql: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "exec", "-i", DB_CONTAINER, "sh", "-c", PSQL],
        input=sql,
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
        timeout=60,
    )


def _query(sql: str) -> list[str]:
    result = _psql(sql)
    assert result.returncode == 0, result.stderr
    return [line for line in result.stdout.splitlines() if line]


def _assert_fails(sql: str, expected_error: str) -> None:
    result = _psql(f"BEGIN;\n{sql}\nROLLBACK;")
    assert result.returncode != 0, "Era esperado erro de constraint do PostgreSQL"
    assert expected_error in result.stderr, (
        f"Esperado '{expected_error}' em stderr, obtido: {result.stderr}"
    )


requires_db = pytest.mark.skipif(
    not _is_db_ready(),
    reason=(
        f"Container {DB_CONTAINER} não está em execução "
        "(inicie com docker compose up -d db)"
    ),
)


@pytest.mark.integration
@requires_db
class TestContinuousAggregates:
    def test_continuous_aggregates_exist_with_expected_columns(self):
        views = _query(
            """
            SELECT view_name, hypertable_name
            FROM timescaledb_information.continuous_aggregates
            WHERE view_name IN ('telemetry_hourly', 'telemetry_daily')
            ORDER BY view_name;
            """
        )
        assert views == [
            "telemetry_daily|telemetry_events",
            "telemetry_hourly|telemetry_events",
        ]

        for view_name in ("telemetry_hourly", "telemetry_daily"):
            cols = _query(
                f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = '{view_name}'
                ORDER BY ordinal_position;
                """
            )
            assert cols == EXPECTED_AGGREGATE_COLUMNS

    def test_continuous_aggregate_refresh_policies(self):
        rows = _query(
            """
            SELECT
                ca.view_name,
                (
                    (ca.view_name = 'telemetry_hourly'
                     AND (j.config ->> 'start_offset')::interval
                         = INTERVAL '3 hours'
                     AND (j.config ->> 'end_offset')::interval
                         = INTERVAL '1 hour'
                     AND j.schedule_interval = INTERVAL '15 minutes')
                    OR
                    (ca.view_name = 'telemetry_daily'
                     AND (j.config ->> 'start_offset')::interval
                         = INTERVAL '3 days'
                     AND (j.config ->> 'end_offset')::interval
                         = INTERVAL '1 day'
                     AND j.schedule_interval = INTERVAL '1 hour')
                )
            FROM timescaledb_information.jobs j
            JOIN timescaledb_information.continuous_aggregates ca
              ON (
                  j.hypertable_schema = ca.view_schema
                  AND j.hypertable_name = ca.view_name
              ) OR (
                  j.hypertable_schema = ca.materialization_hypertable_schema
                  AND j.hypertable_name = ca.materialization_hypertable_name
              )
            WHERE j.proc_name = 'policy_refresh_continuous_aggregate'
              AND ca.view_name IN ('telemetry_hourly', 'telemetry_daily')
            ORDER BY ca.view_name;
            """
        )
        assert rows == ["telemetry_daily|t", "telemetry_hourly|t"]

    def test_continuous_aggregate_retention_policies_are_five_years(self):
        rows = _query(
            """
            SELECT
                ca.view_name,
                (j.config ->> 'drop_after')::interval = INTERVAL '5 years'
            FROM timescaledb_information.jobs j
            JOIN timescaledb_information.continuous_aggregates ca
              ON (
                  j.hypertable_schema = ca.view_schema
                  AND j.hypertable_name = ca.view_name
              ) OR (
                  j.hypertable_schema = ca.materialization_hypertable_schema
                  AND j.hypertable_name = ca.materialization_hypertable_name
              )
            WHERE j.proc_name = 'policy_retention'
              AND ca.view_name IN ('telemetry_hourly', 'telemetry_daily')
            ORDER BY ca.view_name;
            """
        )
        assert rows == ["telemetry_daily|t", "telemetry_hourly|t"]

    def test_aggregates_script_can_be_reapplied_idempotently(self):
        result = _psql(AGGREGATES_SQL.read_text(encoding="utf-8"))
        assert result.returncode == 0, result.stderr

        rows = _query(
            """
            SELECT ca.view_name, j.proc_name, count(*)
            FROM timescaledb_information.jobs j
            JOIN timescaledb_information.continuous_aggregates ca
              ON (
                  j.hypertable_schema = ca.view_schema
                  AND j.hypertable_name = ca.view_name
              ) OR (
                  j.hypertable_schema = ca.materialization_hypertable_schema
                  AND j.hypertable_name = ca.materialization_hypertable_name
              )
            WHERE ca.view_name IN ('telemetry_hourly', 'telemetry_daily')
              AND j.proc_name IN (
                  'policy_refresh_continuous_aggregate',
                  'policy_retention'
              )
            GROUP BY ca.view_name, j.proc_name
            ORDER BY ca.view_name, j.proc_name;
            """
        )
        assert rows == [
            "telemetry_daily|policy_refresh_continuous_aggregate|1",
            "telemetry_daily|policy_retention|1",
            "telemetry_hourly|policy_refresh_continuous_aggregate|1",
            "telemetry_hourly|policy_retention|1",
        ]


@pytest.mark.integration
@requires_db
class TestRelationalSchema:
    def test_pgcrypto_extension_is_installed(self):
        rows = _query(
            "SELECT extname FROM pg_extension WHERE extname = 'pgcrypto';"
        )
        assert rows == ["pgcrypto"]

    def test_all_twelve_tables_exist_with_expected_columns(self):
        for table_name, expected_cols in EXPECTED_RELATIONAL_TABLES.items():
            rows = _query(
                f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = '{table_name}'
                ORDER BY ordinal_position;
                """
            )
            assert rows == expected_cols, f"Colunas divergentes em {table_name}"

    def test_required_indexes_exist(self):
        rows = _query(
            """
            SELECT indexname, tablename, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public';
            """
        )
        found: dict[str, tuple[str, str]] = {}
        for row in rows:
            index_name, table_name, index_def = row.split("|", 2)
            match = re.search(r"\((.*)\)$", index_def)
            if not match:
                continue
            found[index_name] = (table_name, match.group(1).replace('"', ""))

        for index_name, (expected_table, expected_cols) in EXPECTED_INDEXES.items():
            assert index_name in found
            assert found[index_name] == (expected_table, expected_cols)

    def test_check_and_unique_constraints_are_enforced(self):
        uid = uuid.uuid4()

        _assert_fails(
            f"""
            INSERT INTO admin_users (id, email, name, password_hash, role)
            VALUES ('{uid}', 'a@fatec.sp.gov.br', 'Admin', 'hash', 'super_unknown');
            """,
            "admin_users_role_check",
        )
        _assert_fails(
            f"""
            INSERT INTO admin_users (id, email, name, password_hash, role)
            VALUES (
                '{uid}', 'dup@fatec.sp.gov.br', 'Admin 1', 'hash', 'coordenador'
            );
            INSERT INTO admin_users (id, email, name, password_hash, role)
            VALUES (
                '{uuid.uuid4()}', 'dup@fatec.sp.gov.br', 'Admin 2', 'hash', 'editor'
            );
            """,
            "admin_users_email_key",
        )

        _assert_fails(
            """
            INSERT INTO course_info
                (slug, title, summary, graduate_profile, duration_semesters,
                 shifts, admission_forms, status)
            VALUES ('dsm', 'DSM', 'Resumo', 'Perfil', 0, '[]', '[]', 'publicado');
            """,
            "course_info_duration_semesters_check",
        )
        _assert_fails(
            """
            INSERT INTO course_info
                (slug, title, summary, graduate_profile, duration_semesters,
                 shifts, admission_forms, status)
            VALUES (
                'dsm', 'DSM', 'Resumo', 'Perfil', 6, '[]', '[]', 'invalid_status'
            );
            """,
            "course_info_status_check",
        )
        _assert_fails(
            """
            INSERT INTO course_info
                (slug, title, summary, graduate_profile, duration_semesters,
                 shifts, admission_forms, status)
            VALUES
                ('dsm-dup', 'DSM', 'Resumo', 'Perfil', 6, '[]', '[]', 'publicado'),
                ('dsm-dup', 'DSM 2', 'Resumo', 'Perfil', 6, '[]', '[]', 'rascunho');
            """,
            "course_info_slug_key",
        )

        _assert_fails(
            """
            INSERT INTO curriculum_subjects
                (code, name, semester, workload_hours, description, status)
            VALUES ('DSM001', 'Algoritmos', 7, 80, 'Desc', 'publicado');
            """,
            "curriculum_subjects_semester_check",
        )
        _assert_fails(
            """
            INSERT INTO curriculum_subjects
                (code, name, semester, workload_hours, description, status)
            VALUES ('DSM001', 'Algoritmos', 1, 0, 'Desc', 'publicado');
            """,
            "curriculum_subjects_workload_hours_check",
        )
        _assert_fails(
            """
            INSERT INTO curriculum_subjects
                (code, name, semester, workload_hours, description, status)
            VALUES ('DSM001', 'Algoritmos', 1, 80, 'Desc', 'invalid_status');
            """,
            "curriculum_subjects_status_check",
        )
        _assert_fails(
            """
            INSERT INTO curriculum_subjects
                (code, name, semester, workload_hours, description, status)
            VALUES
                ('DSM-DUP', 'Algoritmos', 1, 80, 'Desc', 'publicado'),
                ('DSM-DUP', 'Estrutura', 2, 80, 'Desc', 'rascunho');
            """,
            "curriculum_subjects_code_key",
        )

        _assert_fails(
            """
            INSERT INTO projects
                (title, summary, description, technologies, semester_label,
                 authors, status)
            VALUES ('Proj', 'Sum', 'Desc', '[]', '1º Sem', '[]', 'invalid_status');
            """,
            "projects_status_check",
        )
        _assert_fails(
            """
            INSERT INTO faqs (question, answer, display_order, status)
            VALUES ('Pergunta?', 'Resposta.', 1, 'invalid_status');
            """,
            "faqs_status_check",
        )
        _assert_fails(
            """
            INSERT INTO quiz_questions (prompt, display_order, status)
            VALUES ('Qual área?', 1, 'invalid_status');
            """,
            "quiz_questions_status_check",
        )

        _assert_fails(
            """
            INSERT INTO testimonials
                (author_name, author_role, quote, status)
            VALUES ('Maria', 'visitante_invalido', 'Ótimo curso', 'publicado');
            """,
            "testimonials_author_role_check",
        )
        _assert_fails(
            """
            INSERT INTO testimonials
                (author_name, author_role, graduation_year, quote, status)
            VALUES ('Maria', 'egresso', 2000, 'Ótimo curso', 'publicado');
            """,
            "testimonials_graduation_year_check",
        )
        _assert_fails(
            """
            INSERT INTO testimonials
                (author_name, author_role, quote, status)
            VALUES ('Maria', 'estudante', 'Ótimo curso', 'invalid_status');
            """,
            "testimonials_status_check",
        )

        _assert_fails(
            """
            INSERT INTO events
                (title, description, event_type, location_name, starts_at,
                 ends_at, qr_token, status)
            VALUES (
                'Evento', 'Desc', 'tipo_invalido', 'Auditório',
                '2026-11-22 10:00:00+00', '2026-11-22 12:00:00+00',
                'tok-1', 'publicado'
            );
            """,
            "events_event_type_check",
        )
        _assert_fails(
            """
            INSERT INTO events
                (title, description, event_type, location_name, starts_at,
                 ends_at, qr_token, status)
            VALUES (
                'Evento', 'Desc', 'palestra', 'Auditório',
                '2026-11-22 12:00:00+00', '2026-11-22 10:00:00+00',
                'tok-2', 'publicado'
            );
            """,
            "events_valid_window",
        )
        _assert_fails(
            """
            INSERT INTO events
                (title, description, event_type, location_name, starts_at,
                 ends_at, qr_token, status)
            VALUES (
                'Evento', 'Desc', 'palestra', 'Auditório',
                '2026-11-22 10:00:00+00', '2026-11-22 10:00:00+00',
                'tok-2b', 'publicado'
            );
            """,
            "events_valid_window",
        )
        _assert_fails(
            """
            INSERT INTO events
                (title, description, event_type, location_name, latitude,
                 starts_at, ends_at, qr_token, status)
            VALUES (
                'Evento', 'Desc', 'palestra', 'Auditório', 95,
                '2026-11-22 10:00:00+00', '2026-11-22 12:00:00+00',
                'tok-3', 'publicado'
            );
            """,
            "events_latitude_check",
        )
        _assert_fails(
            """
            INSERT INTO events
                (title, description, event_type, location_name, longitude,
                 starts_at, ends_at, qr_token, status)
            VALUES (
                'Evento', 'Desc', 'palestra', 'Auditório', 185,
                '2026-11-22 10:00:00+00', '2026-11-22 12:00:00+00',
                'tok-4', 'publicado'
            );
            """,
            "events_longitude_check",
        )
        _assert_fails(
            """
            INSERT INTO events
                (title, description, event_type, location_name, starts_at,
                 ends_at, qr_token, status)
            VALUES
                ('E1', 'Desc', 'palestra', 'Lab 1',
                 '2026-11-22 10:00:00+00', '2026-11-22 12:00:00+00',
                 'tok-dup', 'publicado'),
                ('E2', 'Desc', 'feira', 'Lab 2',
                 '2026-11-22 14:00:00+00', '2026-11-22 16:00:00+00',
                 'tok-dup', 'publicado');
            """,
            "events_qr_token_key",
        )
        _assert_fails(
            """
            INSERT INTO events
                (title, description, event_type, location_name, starts_at,
                 ends_at, qr_token, status)
            VALUES (
                'Evento', 'Desc', 'palestra', 'Auditório',
                '2026-11-22 10:00:00+00', '2026-11-22 12:00:00+00',
                'tok-5', 'invalid_status'
            );
            """,
            "events_status_check",
        )

        q_id = uuid.uuid4()
        _assert_fails(
            f"""
            INSERT INTO quiz_questions (id, prompt, display_order, status)
            VALUES ('{q_id}', 'Pergunta', 1, 'publicado');
            INSERT INTO quiz_options
                (question_id, label, display_order, weight_frontend_mobile,
                 weight_backend_dados, weight_infra_iot, weight_fullstack)
            VALUES ('{q_id}', 'Opção A', 1, -1, 0, 0, 0);
            """,
            "quiz_options_weight_frontend_mobile_check",
        )
        cascade_quiz = _query(
            f"""
            BEGIN;
            INSERT INTO quiz_questions (id, prompt, display_order, status)
            VALUES ('{q_id}', 'Pergunta cascade', 1, 'publicado');
            INSERT INTO quiz_options
                (question_id, label, display_order, weight_frontend_mobile,
                 weight_backend_dados, weight_infra_iot, weight_fullstack)
            VALUES ('{q_id}', 'Opção cascade', 1, 1, 0, 0, 0);
            DELETE FROM quiz_questions WHERE id = '{q_id}';
            SELECT count(*) FROM quiz_options WHERE question_id = '{q_id}';
            ROLLBACK;
            """
        )
        assert cascade_quiz == ["0"]

        e_id = uuid.uuid4()
        s_id = uuid.uuid4()
        _assert_fails(
            f"""
            INSERT INTO events
                (id, title, description, event_type, location_name, starts_at,
                 ends_at, qr_token, status)
            VALUES (
                '{e_id}', 'Evento', 'Desc', 'palestra', 'Auditório',
                '2026-11-22 10:00:00+00', '2026-11-22 12:00:00+00',
                'tok-chk-1', 'publicado'
            );
            INSERT INTO event_checkins (event_id, session_id, method)
            VALUES ('{e_id}', '{s_id}', 'metodo_invalido');
            """,
            "event_checkins_method_check",
        )
        _assert_fails(
            f"""
            INSERT INTO events
                (id, title, description, event_type, location_name, starts_at,
                 ends_at, qr_token, status)
            VALUES (
                '{e_id}', 'Evento', 'Desc', 'palestra', 'Auditório',
                '2026-11-22 10:00:00+00', '2026-11-22 12:00:00+00',
                'tok-chk-2', 'publicado'
            );
            INSERT INTO event_checkins (event_id, session_id, method, latitude)
            VALUES ('{e_id}', '{s_id}', 'qr_code', -95);
            """,
            "event_checkins_latitude_check",
        )
        _assert_fails(
            f"""
            INSERT INTO events
                (id, title, description, event_type, location_name, starts_at,
                 ends_at, qr_token, status)
            VALUES (
                '{e_id}', 'Evento', 'Desc', 'palestra', 'Auditório',
                '2026-11-22 10:00:00+00', '2026-11-22 12:00:00+00',
                'tok-chk-3', 'publicado'
            );
            INSERT INTO event_checkins
                (event_id, session_id, method, distance_meters)
            VALUES ('{e_id}', '{s_id}', 'qr_code', -1);
            """,
            "event_checkins_distance_meters_check",
        )
        _assert_fails(
            f"""
            INSERT INTO events
                (id, title, description, event_type, location_name, starts_at,
                 ends_at, qr_token, status)
            VALUES (
                '{e_id}', 'Evento', 'Desc', 'palestra', 'Auditório',
                '2026-11-22 10:00:00+00', '2026-11-22 12:00:00+00',
                'tok-chk-4', 'publicado'
            );
            INSERT INTO event_checkins (event_id, session_id, method)
            VALUES
                ('{e_id}', '{s_id}', 'qr_code'),
                ('{e_id}', '{s_id}', 'qr_code');
            """,
            "event_checkins_unique_session_event",
        )
        cascade_event = _query(
            f"""
            BEGIN;
            INSERT INTO events
                (id, title, description, event_type, location_name, starts_at,
                 ends_at, qr_token, status)
            VALUES (
                '{e_id}', 'Evento cascade', 'Desc', 'palestra', 'Auditório',
                '2026-11-22 10:00:00+00', '2026-11-22 12:00:00+00',
                'tok-chk-cascade', 'publicado'
            );
            INSERT INTO event_checkins (event_id, session_id, method)
            VALUES ('{e_id}', '{s_id}', 'qr_code');
            DELETE FROM events WHERE id = '{e_id}';
            SELECT count(*) FROM event_checkins WHERE event_id = '{e_id}';
            ROLLBACK;
            """
        )
        assert cascade_event == ["0"]

        _assert_fails(
            f"""
            INSERT INTO quiz_submissions
                (session_id, answers, scores, percentages, dominant_profile)
            VALUES ('{s_id}', '{{}}', '{{}}', '{{}}', 'perfil_invalido');
            """,
            "quiz_submissions_dominant_profile_check",
        )

    def test_all_three_init_scripts_can_be_reapplied_in_order(self):
        for script in (INIT_TIMESCALEDB_SQL, AGGREGATES_SQL, RELATIONAL_SQL):
            result = _psql(script.read_text(encoding="utf-8"))
            assert result.returncode == 0, f"{script.name}: {result.stderr}"
