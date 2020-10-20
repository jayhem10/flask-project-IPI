import os
import firebase_admin
import pyrebase
import json
from firebase_admin import credentials, auth, firestore
from flask import Flask, render_template, url_for, flash, request
from flask_wtf.csrf import CSRFProtect
from app.forms import SigninForm, SignupForm


app = Flask(__name__)

SECRET_KEY = os.urandom(32)
app.config['SECRET_KEY'] = SECRET_KEY

if not firebase_admin._apps:
    cred = credentials.Certificate('fbAdminConfig.json')
    firebase = firebase_admin.initialize_app(cred)
pb = pyrebase.initialize_app(json.load(open('fbconfig.json')))

db = firestore.client()
users = db.collection('users')


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
        try:
            user = auth.create_user(
                email=request.form['email'],
                password=request.form['password']
            )
            users.document(user.uid).set({
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

    
