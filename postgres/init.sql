/*CREATE TABLE: creates our telemetry storage table.
SERIAL PRIMARY KEY: gives every speed test a unique ID.
TIMESTAMPTZ: records the timestamp, including timezone awareness.
FLOAT: stores the speed and latency measurements.
CREATE INDEX: makes timestamp-based Grafana queries faster. */


CREATE TABLE IF NOT EXISTS speedtest_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    download_speed FLOAT,
    upload_speed FLOAT,
    ping FLOAT,
    jitter FLOAT
);

CREATE INDEX IF NOT EXISTS idx_speedtest_timestamp
ON speedtest_logs(timestamp);
