from flask import Flask, jsonify, request
import redis
import requests
from flask_cors import CORS
import time
import os

# OpenTelemetry imports
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize OpenTelemetry Tracing
trace.set_tracer_provider(TracerProvider())
otlp_trace_exporter = OTLPSpanExporter(endpoint="http://otel-collector:4318/v1/traces")
span_processor = BatchSpanProcessor(otlp_trace_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Initialize OpenTelemetry Metrics
metric_reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint="http://otel-collector:4318/v1/metrics")
)
meter_provider = MeterProvider(metric_readers=[metric_reader])

# Instrument Flask, Requests, and Redis
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()
RedisInstrumentor().instrument()

# Create metrics
meter = meter_provider.get_meter("backend-a")
request_counter = meter.create_counter(
    "http_requests_total",
    description="Total HTTP requests"
)
request_duration = meter.create_histogram(
    "http_request_duration_seconds",
    description="HTTP request duration in seconds"
)

# Create frontend metrics meter for collecting frontend data
frontend_meter = meter_provider.get_meter("frontend")
page_load_time = frontend_meter.create_histogram(
    "frontend_page_load_seconds",
    description="Frontend page load time in seconds"
)
api_call_time = frontend_meter.create_histogram(
    "frontend_api_call_seconds",
    description="Frontend API call duration in seconds"
)

# Initialize Redis client
redis_client = redis.StrictRedis(host='redis', port=6379, db=0, decode_responses=True)

@app.route("/get_user_data")
def get_user_data():
    tracer = trace.get_tracer(__name__)
    start_time = time.time()

    with tracer.start_as_current_span("get_user_data") as span:
        try:
            request_counter.add(1, {"endpoint": "/get_user_data", "method": "GET"})
            
            # First, fetch from Redis
            with tracer.start_as_current_span("redis_operations"):
                username = redis_client.get('username')
                department = redis_client.get('department')
                span.set_attribute("redis.keys_fetched", 2)

            if not username or not department:
                span.set_status(trace.Status(trace.StatusCode.ERROR, "Data not found in Redis"))
                return jsonify({"error": "Data not found in Redis"}), 404

            # Fetch from Backend B
            with tracer.start_as_current_span("call_backend_b"):
                response = requests.get("http://backend-b:5002/get_timestamp_from_backend_b")
                span.set_attribute("backend_b.status_code", response.status_code)

            if response.status_code == 200:
                backend_b_data = response.json()
                timestamp = backend_b_data.get('timestamp')

                # Call Backend D to format timestamp into human-readable form
                with tracer.start_as_current_span("call_backend_d"):
                    try:
                        d_resp = requests.post(
                            "http://backend-d:5004/format_time",
                            json={"timestamp": timestamp},
                            timeout=3,
                        )
                        span.set_attribute("backend_d.status_code", d_resp.status_code)
                        if d_resp.status_code == 200:
                            formatted = d_resp.json().get('formatted')
                        else:
                            formatted = None
                    except Exception as e:
                        span.record_exception(e)
                        formatted = None

                # Record success metrics
                duration = time.time() - start_time
                request_duration.record(duration, {"endpoint": "/get_user_data", "status": "success"})
                
                return jsonify({
                    "username": username,
                    "department": department,
                    "timestamp": timestamp,
                    "timestamp_human": formatted
                })
            else:
                span.set_status(trace.Status(trace.StatusCode.ERROR, "Backend B call failed"))
                request_duration.record(time.time() - start_time, {"endpoint": "/get_user_data", "status": "error"})
                return jsonify({"error": "Failed to fetch timestamp from Backend B"}), 500

        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            request_duration.record(time.time() - start_time, {"endpoint": "/get_user_data", "status": "error"})
            return jsonify({"error": str(e)}), 500

@app.route("/health")
def health():
    return jsonify({"status": "healthy"})

# Frontend Metrics Handling (New Endpoint)
@app.route("/frontend_metrics", methods=["POST"])
def frontend_metrics():
    data = request.get_json()
    try:
        # Record frontend page load time
        if data.get('event') == 'page_load':
            page_load_time.record(data.get('loadTime', 0) / 1000)  # Convert to seconds
        # Record frontend API call time
        elif data.get('event') == 'api_call':
            api_call_time.record(data.get('duration', 0) / 1000)  # Convert to seconds
        return jsonify({"status": "received"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
