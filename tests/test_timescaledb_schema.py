import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
INIT_SQL = REPO_ROOT / "deployments" / "docker" / "init-timescaledb.sql"
COMPOSE_FILE = REPO_ROOT / "deployments" / "docker-compose.yml"

DB_CONTAINER = os.getenv("DB_CONTAINER", "dsm_db")
PSQL = 'psql -X -q -t -A -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'


def _init_sql_without_comments() -> str:
    return re.sub(r"--[^\n]*", "", INIT_SQL.read_text(encoding="utf-8"))


def test_db_service_runs_init_script_on_first_boot():
    compose = COMPOSE_FILE.read_text(encoding="utf-8")

    assert "./docker/init-timescaledb.sql:/docker-entrypoint-initdb.d/" in compose


def test_init_script_ddl_tolerates_existing_objects():
    sql = _init_sql_without_comments()

    unguarded = re.findall(
        r"\bCREATE\s+(?:TABLE|INDEX|EXTENSION)\b(?!\s+IF\s+NOT\s+EXISTS)",
        sql,
        re.IGNORECASE,
    )

    assert unguarded == []


@pytest.mark.parametrize(
    "function",
    ["create_hypertable", "add_compression_policy", "add_retention_policy"],
)
def test_timescaledb_calls_tolerate_existing_objects(function):
    sql = _init_sql_without_comments()

    calls = re.findall(
        rf"\b{function}\s*\((.*?)\)\s*;", sql, re.IGNORECASE | re.DOTALL
    )

    assert len(calls) == 1
    assert re.search(r"if_not_exists\s*=>\s*TRUE", calls[0], re.IGNORECASE)


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


requires_db = pytest.mark.skipif(
    not _is_db_ready(),
    reason=(
        f"Container {DB_CONTAINER} não está em execução "
        "(inicie com docker compose up -d db)"
    ),
)


@pytest.mark.integration
@requires_db
class TestTelemetryEventsHypertable:
    def test_columns_are_strictly_typed_and_required(self):
        rows = _query(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'telemetry_events'
            ORDER BY ordinal_position;
            """
        )

        assert rows == [
            "event_id|uuid|NO",
            "timestamp|timestamp with time zone|NO",
            "session_id|uuid|NO",
            "source|character varying|NO",
            "category|character varying|NO",
            "payload|jsonb|NO",
            "created_at|timestamp with time zone|NO",
        ]

    def test_primary_key_is_event_id_and_timestamp(self):
        rows = _query(
            """
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a
              ON a.attrelid = i.indrelid AND a.attnum = ANY (i.indkey)
            WHERE i.indrelid = 'telemetry_events'::regclass AND i.indisprimary;
            """
        )

        assert sorted(rows) == ["event_id", "timestamp"]

    def test_is_partitioned_by_timestamp_in_7_day_chunks(self):
        rows = _query(
            """
            SELECT column_name, time_interval = INTERVAL '7 days'
            FROM timescaledb_information.dimensions
            WHERE hypertable_name = 'telemetry_events';
            """
        )

        assert rows == ["timestamp|t"]

    def test_dashboard_composite_indexes_exist(self):
        rows = _query(
            """
            SELECT indexdef FROM pg_indexes
            WHERE tablename = 'telemetry_events';
            """
        )
        index_columns = {
            re.search(r"\((.*)\)$", row).group(1).replace('"', "") for row in rows
        }

        assert "timestamp DESC, category" in index_columns
        assert "session_id, timestamp DESC" in index_columns

    def test_raw_events_are_dropped_after_90_days(self):
        rows = _query(
            """
            SELECT count(*)
            FROM timescaledb_information.jobs
            WHERE hypertable_name = 'telemetry_events'
              AND proc_name = 'policy_retention'
              AND (config ->> 'drop_after')::interval = INTERVAL '90 days';
            """
        )

        assert rows == ["1"]

    def test_chunks_are_compressed_after_14_days(self):
        rows = _query(
            """
            SELECT
                (SELECT compression_enabled
                 FROM timescaledb_information.hypertables
                 WHERE hypertable_name = 'telemetry_events'),
                (SELECT count(*)
                 FROM timescaledb_information.jobs
                 WHERE hypertable_name = 'telemetry_events'
                   AND proc_name = 'policy_compression'
                   AND (config ->> 'compress_after')::interval
                       = INTERVAL '14 days');
            """
        )

        assert rows == ["t|1"]

    def test_duplicate_event_is_ignored_on_conflict(self):
        event_id = uuid.uuid4()
        insert = f"""
            INSERT INTO telemetry_events
                (event_id, timestamp, session_id, source, category, payload)
            VALUES (
                '{event_id}', now(), '{uuid.uuid4()}',
                'app_mobile', 'interacao_tela', '{{"screen_name": "home"}}'
            )
            ON CONFLICT (event_id, timestamp) DO NOTHING;
        """

        rows = _query(
            f"""
            BEGIN;
            {insert}
            {insert}
            SELECT count(*) FROM telemetry_events WHERE event_id = '{event_id}';
            ROLLBACK;
            """
        )

        assert rows == ["1"]

    def test_reapply_and_duplicate_insert_on_compressed_chunk(self):
        event_id = uuid.uuid4()
        # now() é fixo dentro da transação, então os dois INSERTs geram o mesmo
        # timestamp e o segundo colide com a linha já comprimida.
        event_ts = "now() - INTERVAL '20 days'"
        insert = f"""
            INSERT INTO telemetry_events
                (event_id, timestamp, session_id, source, category, payload)
            VALUES (
                '{event_id}', {event_ts}, '{uuid.uuid4()}',
                'app_mobile', 'interacao_tela', '{{"screen_name": "home"}}'
            )
            ON CONFLICT (event_id, timestamp) DO NOTHING;
        """
        event_chunk = f"""
            FROM timescaledb_information.chunks
            WHERE hypertable_name = 'telemetry_events'
              AND range_start <= {event_ts} AND range_end > {event_ts}
        """
        init_sql = INIT_SQL.read_text(encoding="utf-8")

        rows = _query(
            f"""
            BEGIN;
            {insert}
            \\o /dev/null
            SELECT compress_chunk(
                format('%I.%I', chunk_schema, chunk_name)::regclass,
                if_not_compressed => TRUE
            )
            {event_chunk};
            {init_sql}
            \\o
            {insert}
            SELECT is_compressed {event_chunk};
            SELECT count(*) FROM telemetry_events WHERE event_id = '{event_id}';
            ROLLBACK;
            """
        )

        assert rows == ["t", "1"]

    def test_init_script_can_be_reapplied(self):
        result = _psql(INIT_SQL.read_text(encoding="utf-8"))

        assert result.returncode == 0, result.stderr
        policies = _query(
            """
            SELECT proc_name, count(*)
            FROM timescaledb_information.jobs
            WHERE hypertable_name = 'telemetry_events'
            GROUP BY proc_name
            ORDER BY proc_name;
            """
        )
        assert policies == ["policy_compression|1", "policy_retention|1"]
