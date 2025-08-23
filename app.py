from flask import Flask

# create a Flask app
app = Flask(__name__)

# define a simple route
@app.route("/")
def home():
    return "Hello, Flask!"

# run the app
if __name__ == "__main__":
    app.run(debug=True)

