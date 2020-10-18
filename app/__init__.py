# app/__init__.py
from flask import Flask
from flask import render_template
app = Flask(__name__)


@app.route('/')
def home():
    user = {'username': 'Antonin'}
    return render_template('index.html', title='Page principale', user=user)
