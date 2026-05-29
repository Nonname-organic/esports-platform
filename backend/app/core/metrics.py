"""
Prometheus metrics registry.

Import individual metrics from here to increment them from anywhere in the app:

    from app.core.metrics import matches_processed_total
    matches_processed_total.labels(game="VALORANT", outcome="win").inc()
"""
from prometheus_client import Counter, Gauge, Histogram, Info

# ── HTTP ──────────────────────────────────────────────────────────────────────

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests received",
    ["method", "path", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

# ── WebSocket ─────────────────────────────────────────────────────────────────

ws_connections_active = Gauge(
    "esports_ws_connections_active",
    "Currently open WebSocket connections",
    ["room_type"],  # match | bracket
)

# ── Worker ────────────────────────────────────────────────────────────────────

worker_jobs_total = Counter(
    "esports_worker_jobs_total",
    "Total SQS jobs processed by the worker",
    ["event_type", "status"],  # status: success | error
)

sqs_queue_depth = Gauge(
    "esports_sqs_queue_depth",
    "Approximate number of visible messages in an SQS queue",
    ["queue"],
)

# ── Business ──────────────────────────────────────────────────────────────────

matches_processed_total = Counter(
    "esports_matches_processed_total",
    "Total match results registered and processed",
    ["game"],
)

analytics_events_total = Counter(
    "esports_analytics_events_total",
    "Total analytics events written to the DB or exported to S3",
    ["event_type", "destination"],  # destination: db | s3
)

active_tournaments_gauge = Gauge(
    "esports_active_tournaments_total",
    "Number of currently active (in-progress) tournaments",
)

# ── Application info ──────────────────────────────────────────────────────────

app_info = Info(
    "esports_app",
    "Static application metadata",
)
