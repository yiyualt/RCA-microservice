from flask import Flask, jsonify
import random
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
from flask_cors import CORS

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
meter = meter_provider.get_meter("backend-c")
quote_counter = meter.create_counter(
    "quote_requests_total",
    description="Total quote requests"
)

# Create histogram to track request duration (latency)
request_duration = meter.create_histogram(
    "quote_request_duration_seconds",
    description="Quote request duration in seconds"
)

QUOTES = [
    "Stay hungry, stay foolish.",
    "Simplicity is the ultimate sophistication.",
    "Premature optimization is the root of all evil.",
    "Programs must be written for people to read.",
    "Talk is cheap. Show me the code.",
]

@app.route("/get_random_quote")
def get_random_quote():
    tracer = trace.get_tracer(__name__)
    start_time = time.time()
    
    with tracer.start_as_current_span("get_random_quote"):
        quote_counter.add(1)
        quote = random.choice(QUOTES)
        duration = time.time() - start_time
        request_duration.record(duration, {"endpoint": "/get_random_quote"})
        return jsonify({"quote": quote})

@app.route("/health")
def health():
    return jsonify({"status": "healthy"})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5003)


