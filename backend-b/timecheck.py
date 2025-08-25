from flask import Flask, jsonify
from datetime import datetime
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
meter = meter_provider.get_meter("backend-b")
timestamp_counter = meter.create_counter(
    "timestamp_requests_total",
    description="Total timestamp requests"
)

# Create histogram to track request duration (latency)
request_duration = meter.create_histogram(
    "timestamp_request_duration_seconds",
    description="Timestamp request duration in seconds"
)

@app.route("/get_timestamp_from_backend_b")
def get_timestamp_from_backend_b():
    tracer = trace.get_tracer(__name__)
    start_time = time.time()
    
    with tracer.start_as_current_span("get_timestamp"):
        timestamp_counter.add(1)
        
        # Fetch the current timestamp
        timestamp = datetime.now().isoformat()
        
        # Record the request duration
        duration = time.time() - start_time
        request_duration.record(duration, {"endpoint": "/get_timestamp_from_backend_b"})
        
        return jsonify({"timestamp": timestamp})

@app.route("/health")
def health():
    return jsonify({"status": "healthy"})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5002)
