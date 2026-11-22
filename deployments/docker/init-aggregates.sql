CREATE MATERIALIZED VIEW IF NOT EXISTS telemetry_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket(INTERVAL '1 hour', timestamp) AS bucket,
    category,
    source,
    COALESCE(payload->>'screen_name', '') AS screen_name,
    COALESCE(payload->>'event_id', '') AS event_ref_id,
    COALESCE(payload->>'dominant_profile', '') AS quiz_profile,
    COUNT(*) AS event_count,
    SUM(
        CASE
            WHEN (payload->>'visitor_count') ~ '^[0-9]+$'
            THEN (payload->>'visitor_count')::BIGINT
            ELSE 0
        END
    ) AS visitor_count_sum,
    AVG(
        CASE
            WHEN (payload->>'duration_seconds') ~ '^[0-9]+(\.[0-9]+)?$'
            THEN (payload->>'duration_seconds')::DOUBLE PRECISION
            ELSE NULL
        END
    ) AS avg_duration_seconds
FROM telemetry_events
GROUP BY 1, 2, 3, 4, 5, 6
WITH NO DATA;

SELECT add_continuous_aggregate_policy(
    'telemetry_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '15 minutes',
    if_not_exists => TRUE
);

SELECT add_retention_policy(
    'telemetry_hourly',
    drop_after => INTERVAL '5 years',
    if_not_exists => TRUE
);

CREATE MATERIALIZED VIEW IF NOT EXISTS telemetry_daily
WITH (timescaledb.continuous) AS
SELECT
    time_bucket(INTERVAL '1 day', timestamp) AS bucket,
    category,
    source,
    COALESCE(payload->>'screen_name', '') AS screen_name,
    COALESCE(payload->>'event_id', '') AS event_ref_id,
    COALESCE(payload->>'dominant_profile', '') AS quiz_profile,
    COUNT(*) AS event_count,
    SUM(
        CASE
            WHEN (payload->>'visitor_count') ~ '^[0-9]+$'
            THEN (payload->>'visitor_count')::BIGINT
            ELSE 0
        END
    ) AS visitor_count_sum,
    AVG(
        CASE
            WHEN (payload->>'duration_seconds') ~ '^[0-9]+(\.[0-9]+)?$'
            THEN (payload->>'duration_seconds')::DOUBLE PRECISION
            ELSE NULL
        END
    ) AS avg_duration_seconds
FROM telemetry_events
GROUP BY 1, 2, 3, 4, 5, 6
WITH NO DATA;

SELECT add_continuous_aggregate_policy(
    'telemetry_daily',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

SELECT add_retention_policy(
    'telemetry_daily',
    drop_after => INTERVAL '5 years',
    if_not_exists => TRUE
);
