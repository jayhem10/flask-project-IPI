import os
import firebase_admin
import pyrebase
import json
from functools import wraps
from firebase_admin import credentials, auth, firestore
from flask import Flask, render_template, url_for, flash, request, session, redirect
from flask_wtf.csrf import CSRFProtect
from app.forms import SigninForm, SignupForm


app = Flask(__name__)


SECRET_KEY = os.urandom(32)
app.config['SECRET_KEY'] = SECRET_KEY

# Connection to firebase
if not firebase_admin._apps:
    cred = credentials.Certificate('fbAdminConfig.json')
    firebase = firebase_admin.initialize_app(cred)
firebase = pyrebase.initialize_app(json.load(open('fbconfig.json')))
# Connection to database
db = firebase.database()
auth = firebase.auth()
users = db.child('users')


def ensure_logged_in(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('user'):
            flash("Connecte toi pour pouvoir accéder à cette page")
            return redirect(url_for('signin'))
        return fn(*args, **kwargs)
    return wrapper


@app.route('/home')
@app.route('/')
def home():
    return render_template("home.html")


@app.route('/account')
@ensure_logged_in
def account():
    flash(f'{session.get("user")}')
    user_id = session.get("user")['localId']
    user = users.child(user_id).get().val()
    flash(f'{user}')
    return render_template("account.html")


@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if session.get('user'):
        return redirect(url_for('account'))

    form = SigninForm()
    if form.validate_on_submit():
        try:
            login = auth.sign_in_with_email_and_password(
                request.form['email'], request.form['password'])
            session['user'] = login
            return redirect(url_for('account'))
        except:
            flash('Une erreur est survenue lors de la connexion')
    return render_template("auth/signin.html", form=form)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if session.get('user'):
        return redirect(url_for('account'))

    form = SignupForm()
    if form.validate_on_submit():
        try:
            user = auth.create_user_with_email_and_password(
                email=request.form['email'],
                password=request.form['password']
            )
            users.child(user['localId']).set({
                'firstname': request.form['firstname'],
                'lastname': request.form['lastname'],
                'description': request.form['description'],
                'email': request.form['email']
            })
            flash('Votre compte a bien été créer vous allez être redirigé')
        except:
            flash('Une erreur est survenue lors de la création de votre compte')
    return render_template("auth/signup.html", form=form)


@app.route('/signout')
def signout():
    session.pop('username')
    return redirect(url_for('home'))


@app.route('/account/profile')
def profile():
        form = SignupForm()
        if form.validate_on_submit():
            try:
       
                users.document(user.uid).set({
                    'firstname': request.form['firstname'],
                    'lastname': request.form['lastname'],
                    'description': request.form['description'],
                    'email': request.form['email']
                })
                flash('Votre compte a bien été modifié vous allez être redirigé')
            except:
                flash('Une erreur est survenue lors de la création de votre compte')    
        return render_template("auth/profile.html", form=form)





if __name__ == "__main__":
    app.run(debug=True)

    
