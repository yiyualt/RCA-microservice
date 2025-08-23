from flask import Flask, jsonify
from flask_cors import CORS  # Import the CORS module

app = Flask(__name__)
CORS(app)  # This enables CORS for all routes

# Define your API route to return user data
@app.route("/get_user_data")
def get_user_data():
    user_data = {
        "username": "yuyi",
        "department": "huawei cloud"
    }
    return jsonify(user_data)  # Return the data as JSON

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
