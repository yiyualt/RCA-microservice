from flask import Flask, jsonify
from datetime import datetime


app = Flask(__name__)

# API route to provide timestamp data
@app.route("/get_timestamp_from_backend_b")
def get_timestamp_from_backend_b():
    # Fetch the current timestamp
    timestamp = datetime.now().isoformat()  # ISO format: "2025-08-24T15:00:00"
    return jsonify({"timestamp": timestamp})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5002)

