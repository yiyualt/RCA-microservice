from flask import Flask, jsonify, request
from flask_cors import CORS
import time

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
meter = meter_provider.get_meter("backend-e")
echo_counter = meter.create_counter(
    "echo_requests_total",
    description="Total echo requests"
)
request_duration = meter.create_histogram(
    "echo_request_duration_seconds",
    description="Echo request duration in seconds"
)

@app.route("/echo", methods=["POST"])
def echo():
    tracer = trace.get_tracer(__name__)
    start_time = time.time()
    with tracer.start_as_current_span("echo"):
        payload = request.get_json(silent=True)
        echo_counter.add(1)
        request_duration.record(time.time() - start_time, {"endpoint": "/echo"})
        return jsonify(payload or {}), 200

@app.route("/health")
def health():
    return jsonify({"status": "healthy"})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5005)


