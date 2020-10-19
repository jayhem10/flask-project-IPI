import os
from flask import Flask, render_template, url_for, flash
from app.forms import SigninForm, SignupForm

app = Flask(__name__)
SECRET_KEY = os.urandom(32)
app.config['SECRET_KEY'] = SECRET_KEY


@app.route('/home')
@app.route('/')
def home():
    return render_template("home.html")


@app.route('/account')
def account():
    return render_template("account.html")


@app.route('/signin')
def signin():
    form = SigninForm()
    return render_template("auth/signin.html", form=form)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        flash('Thanks for registering')
    return render_template("auth/signup.html", form=form)


if __name__ == "__main__":
    app.run(debug=True)
