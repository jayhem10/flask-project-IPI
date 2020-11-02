import os
import firebase_admin
import pyrebase
import json
import datetime
from functools import wraps
from firebase_admin import credentials, auth as auth_admin, firestore
from flask import Flask, render_template, url_for, flash, request, session, redirect
from flask_wtf.csrf import CSRFProtect
from app.forms import SigninForm, SignupForm, ProfileForm, CourseForm
from google.cloud import storage as storage_cloud


app = Flask(__name__)


SECRET_KEY = os.urandom(32)
app.config['SECRET_KEY'] = SECRET_KEY

# Connection to firebase
if not firebase_admin._apps:
    cred = credentials.Certificate('fbAdminConfig.json')
    firebase = firebase_admin.initialize_app(cred)
firebase = pyrebase.initialize_app(json.load(open('fbconfig.json')))


os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "fbAdminConfig.json"


# Connection to databases
dbc = firestore.client()
db = firebase.database()
auth = firebase.auth()
storage = firebase.storage()


def getPdf(link):
    return storage.child(f"{link}").get_url(None)


app.jinja_env.globals.update(getPdf=getPdf)


def ensure_logged_in(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('user'):
            flash("Connecte toi pour pouvoir accéder à cette page")
            return redirect(url_for('signin'))
        return fn(*args, **kwargs)
    return wrapper


def is_my_course(fn):
    @wraps(fn)
    def wrapper(id, *args, **kwargs):
        course_json = dbc.collection('courses').document(id).get()
        course = course_json.to_dict()
        if session.get("user")['localId'] != course['created_by']:
            flash("Ce n'est pas l'un de vos cours !")
            return redirect(url_for('profile'))
        return fn(id, *args, **kwargs)
    return wrapper

# PAGE D'ACCUEIL


@app.route('/home')
@app.route('/')
def home():
    return render_template("home.html")


# GESTION DE L'UTILISATEUR

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if session.get('user'):
        return redirect(url_for('profile'))

    form = SigninForm()
    if form.validate_on_submit():
        try:
            login = auth.sign_in_with_email_and_password(
                request.form['email'], request.form['password'])
            session['user'] = login
            return redirect(url_for('profile'))
        except:
            flash('Une erreur est survenue lors de la connexion')
    return render_template("auth/signin.html", form=form)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if session.get('user'):
        return redirect(url_for('profile'))

    form = SignupForm()
    if form.validate_on_submit():
        try:
            user = auth.create_user_with_email_and_password(
                email=request.form['email'],
                password=request.form['password']
            )
            db.child('users').child(user['localId']).set({
                'firstname': request.form['firstname'],
                'lastname': request.form['lastname'],
                'description': request.form['description'],
                'email': request.form['email']
            })
            link = request.files.get('image', False)
            if link:
                storage.child(f'profile_pictures/{user["localId"]}').put(link)
            flash('Votre compte a bien été créé, connectez-vous !')
            return redirect(url_for('signin'))
        except:
            flash('Une erreur est survenue lors de la création de votre compte')
    return render_template("auth/signup.html", form=form)


@app.route('/signout')
def signout():
    session.clear()
    return redirect(url_for('home'))


@app.route('/profile', methods=['GET'])
@ensure_logged_in
def profile():
    user_id = session.get("user")['localId']
    user = db.child('users').child(user_id).get().val()
    link = storage.child(f"profile_pictures/{user_id}").get_url(None)
    courses = dbc.collection(u'courses').where(
        u'created_by', u'==', user_id).order_by(u'date', direction=firestore.Query.DESCENDING).get()
    try:
        storage.child(f"profile_pictures/{user_id}").download('', 'image')
        os.remove('image')
        image_exist = True
    except:
        image_exist = False

    flash(image_exist)
    flash(f'{session.get("user")}')
    return render_template("profile.html", user=user, image=link, image_exist=image_exist, courses=courses, user_id=user_id)


@app.route('/profile/modify', methods=['GET', 'POST', 'PUT'])
@ensure_logged_in
def modify_profile():
    user = db.child('users').child(session.get("user")['localId']).get().val()
    form = ProfileForm()
    form.lastname.data = user['lastname']
    form.firstname.data = user['firstname']
    form.description.data = user['description']
    if form.validate_on_submit():
        try:
            db.child('users').child(session.get("user")['localId']).update({
                'firstname': request.form['firstname'],
                'lastname': request.form['lastname'],
                'description': request.form['description']
            })
            link = request.files.get('image', False)
            if link:
                image = request.files['image']
                storage.child(
                    f'profile_pictures/{session.get("user")["localId"]}').put(image)

            flash('Votre compte a bien été modifié')
            return redirect(url_for("profile"))
        except:
            flash('Une erreur est survenue lors de la modification de votre compte')
    return render_template("auth/modify_profile.html", form=form, user=user)


@app.route('/delete', methods=['GET', 'POST'])
@ensure_logged_in
def delete():
    user_id = session.get("user")['localId']
    link = f'profile_pictures/{user_id}'
    bucket_name = "flask-ed7bc.appspot.com"
    storage_client = storage_cloud.Client()
    if request.method == "POST":
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(link)
        blob.delete()
        db.child('users').child(session.get("user")['localId']).remove()
        user = auth.current_user['localId']
        auth_admin.delete_user(user)
        session.clear()
        flash("Votre compte a bien été supprimé.")
        return redirect(url_for('home'))
    return render_template("auth/delete.html")


# GESTION DES COURS

# CREER LE COURS
@app.route('/course/create', methods=['GET', 'POST'])
@ensure_logged_in
def create_course():
    form = CourseForm()
    categories = db.child('categories').get().val()
    form.category.choices = categories
    if form.validate_on_submit():
        try:
            ref = dbc.collection('courses').document()
            refImage = storage.child(
                f'courses/{ref.id}').put(request.files['course'])
            ref.set({
                u'title': request.form['title'],
                u'resume': request.form['resume'],
                u'category': request.form['category'],
                u'created_by': session.get("user")['localId'],
                u'date': datetime.datetime.utcnow(),
                u'privacy': form.data.get('privacy'),
                u'image_link': refImage['name']
            })

            flash('Votre cours un bien été créé')
            return redirect(url_for('profile'))
        except:
            flash(
                'Une erreur est survenue lors de la création de votre cours, veillez réessayer')

    return render_template("course/create_course.html", form=form)


# SUPPRIMER LE COURS
@app.route('/course/delete/<id>', methods=['GET', 'POST'])
@ensure_logged_in
@is_my_course
def delete_course(id):
    link = f'courses/{id}'
    bucket_name = "flask-ed7bc.appspot.com"
    storage_client = storage_cloud.Client()
    if request.method == "POST":
        dbc.collection(u'courses').document(id).delete()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(link)
        blob.delete()
        flash("Votre fichier a bien été supprimé.")
        return redirect(url_for('profile'))
    return render_template("course/delete_course.html")


# MODIFIER LE COURS
@app.route('/course/modify/<id>', methods=['GET', 'POST'])
@ensure_logged_in
@is_my_course
def modify_course(id):
    course = dbc.collection(u'courses').document(id).get().to_dict()
    form = CourseForm()
    form.submit.data = "Modifier le cours"
    categories = db.child('categories').get().val()
    form.category.choices = categories
    form.title.data = course[u'title']
    form.resume.data = course[u'resume']
    form.category.data = course[u'category']
    form.privacy.data = course[u'privacy']
    if form.validate_on_submit():
        try:
            ref = dbc.collection('courses').document(id)
            refImage = storage.child(
                f'courses/{ref.id}').put(request.files['course'])
            ref.update({
                u'title': request.form['title'],
                u'resume': request.form['resume'],
                u'category': request.form['category'],
                u'created_by': session.get("user")['localId'],
                u'date': datetime.datetime.utcnow(),
                u'privacy': form.data.get('privacy'),
                u'image_link': refImage['name']
            })

            flash("Votre cours a bien été modifié.")
            return redirect(url_for('profile'))
        except:
            flash(
                'Une erreur est survenue lors de la modification de votre cours, veillez réessayer')
    return render_template("course/modify_course.html", form=form)


# VOIR LE COURS
@app.route('/course/view/<id>', methods=['GET', 'POST'])
@ensure_logged_in
def view_course(id):
    course = dbc.collection('courses').document(id).get().to_dict()

    return render_template("course/view_course.html", course=course)


# CATEGORIES
@app.route('/course/informatique/', methods=['GET', 'POST'])
@ensure_logged_in
def category_info():
        user_id = session.get("user")['localId']
        courses = dbc.collection(u'courses').where(u'created_by', u'==', user_id).where(u'category', u'==', u'Informatique').order_by(u'date', direction=firestore.Query.DESCENDING).get()
       
        return render_template("categories/informatique.html", courses=courses)


@app.route('/course/science/', methods=['GET', 'POST'])
@ensure_logged_in
def category_science():
        user_id = session.get("user")['localId']
        courses = dbc.collection(u'courses').where(u'created_by', u'==', user_id).where(u'category', u'==', u'Sciences').order_by(u'date', direction=firestore.Query.DESCENDING).get()
        return render_template("categories/science.html", courses=courses)




@app.route('/course/history', methods=['GET', 'POST'])
@ensure_logged_in
def category_history():
        user_id = session.get("user")['localId']
        courses = dbc.collection(u'courses').where(u'created_by', u'==', user_id).where(u'category', u'==', u'Histoire').order_by(u'date', direction=firestore.Query.DESCENDING).get()
        return render_template("categories/history.html", courses=courses)




@app.route('/course/medecine', methods=['GET', 'POST'])
@ensure_logged_in
def category_medecine():
        user_id = session.get("user")['localId']
        courses = dbc.collection(u'courses').where(u'created_by', u'==', user_id).where(u'category', u'==', u'Médecine').order_by(u'date', direction=firestore.Query.DESCENDING).get()

        return render_template("categories/medecine.html", courses=courses)




if __name__ == "__main__":
    app.run(debug=True)
