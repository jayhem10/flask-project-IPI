# app/__init__.py
from flask import Flask
from flask import render_template
from flask import url_for
app = Flask(__name__)

@app.route('/home')
@app.route('/')
def home():
    return render_template("home.html")

@app.route('/index')
def index():
    return render_template("index.html")

@app.route('/connection')
def connection():
    return render_template("connection.html")

@app.route('/registration')
def registration():
    return render_template("registration.html")

if __name__ == "__main__":
    app.run(debug=True)