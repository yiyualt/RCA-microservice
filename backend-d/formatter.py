from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.instrumentation.flask import FlaskInstrumentor

app = Flask(__name__)
CORS(app)

# Initialize OpenTelemetry
trace.set_tracer_provider(TracerProvider())
otlp_trace_exporter = OTLPSpanExporter(endpoint="http://otel-collector:4318/v1/traces")
span_processor = BatchSpanProcessor(otlp_trace_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

metric_reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint="http://otel-collector:4318/v1/metrics")
)
meter_provider = MeterProvider(metric_readers=[metric_reader])

# Instrument Flask
FlaskInstrumentor().instrument_app(app)

# Create metrics
meter = meter_provider.get_meter("backend-d")
format_counter = meter.create_counter(
    "format_requests_total",
    description="Total format requests"
)
request_duration = meter.create_histogram(
    "format_request_duration_seconds",
    description="Format request duration in seconds"
)

def to_human_readable(timestamp_iso: str) -> str:
    # Attempt to parse ISO timestamp from backend-b
    try:
        dt = datetime.fromisoformat(timestamp_iso)
    except Exception:
        # Fallback: try removing 'Z' if present
        try:
            if timestamp_iso.endswith('Z'):
                dt = datetime.fromisoformat(timestamp_iso.replace('Z', '+00:00'))
            else:
                raise
        except Exception:
            return "Invalid timestamp"

    # Example: Tuesday, 2025-08-26 14:33:21
    return dt.strftime("%A, %Y-%m-%d %H:%M:%S")

@app.route("/format_time", methods=["POST"])
def format_time():
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("format_time"):
        import time
        start = time.time()
        body = request.get_json(silent=True) or {}
        ts = body.get("timestamp", "")
        format_counter.add(1)
        human = to_human_readable(ts)
        request_duration.record(time.time() - start, {"endpoint": "/format_time"})
        if human == "Invalid timestamp":
            return jsonify({"error": "Invalid timestamp"}), 400
        return jsonify({"formatted": human})

@app.route("/health")
def health():
    return jsonify({"status": "healthy"})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5004)


