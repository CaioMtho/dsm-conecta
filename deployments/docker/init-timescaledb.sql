CREATE EXTENSION IF NOT EXISTS timescaledb;

-- A PK inclui timestamp porque o TimescaleDB exige a coluna de particionamento em
-- todo índice único; ela também é o alvo do ON CONFLICT na deduplicação (RNF07).
CREATE TABLE IF NOT EXISTS telemetry_events (
    event_id   UUID        NOT NULL,
    timestamp  TIMESTAMPTZ NOT NULL,
    session_id UUID        NOT NULL,
    source     VARCHAR(32) NOT NULL,
    category   VARCHAR(64) NOT NULL,
    payload    JSONB       NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT telemetry_events_pkey PRIMARY KEY (event_id, timestamp)
);

COMMENT ON COLUMN telemetry_events.timestamp IS
    'Instante de ocorrência informado pela origem do evento (RF18)';
COMMENT ON COLUMN telemetry_events.created_at IS
    'Instante de persistência do evento pelo ingestor';

-- O índice padrão em (timestamp DESC) seria redundante com o prefixo de
-- idx_telemetry_events_timestamp_category.
SELECT create_hypertable(
    'telemetry_events',
    'timestamp',
    chunk_time_interval => INTERVAL '7 days',
    create_default_indexes => FALSE,
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_telemetry_events_timestamp_category
    ON telemetry_events (timestamp DESC, category);

CREATE INDEX IF NOT EXISTS idx_telemetry_events_session_timestamp
    ON telemetry_events (session_id, timestamp DESC);

-- Reaplicar as configurações de compressão falha quando já existem chunks
-- comprimidos, por isso o ALTER só roda na primeira execução.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM timescaledb_information.hypertables
        WHERE hypertable_name = 'telemetry_events'
          AND compression_enabled
    ) THEN
        -- category (baixa cardinalidade) como segmentby preserva os filtros por
        -- categoria dos dashboards sobre chunks comprimidos; event_id entra no
        -- orderby porque colunas de restrições únicas devem compor segmentby/orderby.
        ALTER TABLE telemetry_events SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'category',
            timescaledb.compress_orderby = 'timestamp DESC, event_id'
        );
    END IF;
END
$$;

SELECT add_compression_policy(
    'telemetry_events',
    compress_after => INTERVAL '14 days',
    if_not_exists => TRUE
);

SELECT add_retention_policy(
    'telemetry_events',
    drop_after => INTERVAL '90 days',
    if_not_exists => TRUE
);
