from flask import Flask, jsonify
import redis
import requests
from flask_cors import CORS 

app = Flask(__name__)
CORS(app)
# Initialize Redis client
redis_client = redis.StrictRedis(host='redis', port=6379, db=0, decode_responses=True)

# API route to get specific data from Redis and Backend B
@app.route("/get_user_data")
def get_user_data():
    try:
        # First, fetch 'username' and 'department' from Redis
        username = redis_client.get('username')
        department = redis_client.get('department')

        if not username or not department:
            return jsonify({"error": "Data not found in Redis"}), 404

        # Now, fetch 'timestamp' from Backend B
        response = requests.get("http://backend-b:5002/get_timestamp_from_backend_b")
        if response.status_code == 200:
            backend_b_data = response.json()
            timestamp = backend_b_data.get('timestamp')

            # Return combined data from Redis and Backend B
            return jsonify({
                "username": username,
                "department": department,
                "timestamp": timestamp
            })
        else:
            return jsonify({"error": "Failed to fetch timestamp from Backend B"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
