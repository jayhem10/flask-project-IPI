from flask import Flask, render_template, url_for


app = Flask(__name__)


@app.route('/home')
@app.route('/')
def home():
    return render_template("home.html")


@app.route('/account')
def account():
    return render_template("account.html")


@app.route('/signin')
def signin():
    return render_template("auth/signin.html")


@app.route('/signup')
def signup():
    return render_template("auth/signup.html")


if __name__ == "__main__":
    app.run(debug=True)
