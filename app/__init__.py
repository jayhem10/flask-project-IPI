import os
import firebase_admin
import pyrebase
import json
import datetime
from functools import wraps
from firebase_admin import credentials, auth as auth_admin, firestore
from flask import Flask, render_template, url_for, flash, request, session, redirect
from flask_wtf.csrf import CSRFProtect
from app.forms import SigninForm, SignupForm, ProfileForm, CourseForm, ResetPassword
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

BUCKET_NAME = "flask-ed7bc.appspot.com"
storage_client = storage_cloud.Client()
bucket = storage_client.bucket(BUCKET_NAME)


def get_pdf(link):
    return storage.child(f"courses/{link}").get_url(None)


app.jinja_env.globals.update(get_pdf=get_pdf)


def user_id():
    if session.get('user'):
        return session.get('user')['localId']


def ensure_logged_in(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('user'):
            flash("Connecte toi pour pouvoir accéder à cette page")
            return redirect(url_for('signin', next=request.url))
        return fn(*args, **kwargs)
    return wrapper


def is_my_course(fn):
    @wraps(fn)
    def test(id, *args, **kwargs):
        course_json = dbc.collection('courses').document(id).get()
        course = course_json.to_dict()
        if user_id() != course['created_by']:
            flash("Ce n'est pas l'un de vos cours !")
            return redirect(url_for('profile'))
        return fn(id, *args, **kwargs)
    return test


@app.route('/home')
@app.route('/')
def home():
    return render_template("home.html")


@app.route('/signin', methods=['GET', 'POST'])
def signin():
    """function for signin"""
    if session.get('user'):
        return redirect(url_for('profile'))
    form = SigninForm()
    if form.validate_on_submit():
        try:
            login = auth.sign_in_with_email_and_password(
                request.form['email'], request.form['password'])
            email_verified = auth.get_account_info(
                login['idToken'])['users'][0]['emailVerified']
            if email_verified:
                session['user'] = login
                next_url = request.form.get("next")
                if next_url:
                    return redirect(next_url)
                return redirect(url_for('profile'))
            else:
                flash(
                    'Vous devez vérifier votre adresse mail ! (Pensez à vérifier vos courriers indésirables)')

        except:
            flash('L\'adresse mail et/ou le mot de passe est incorect')

    return render_template("auth/signin.html", form=form)

@app.route('/reset_password', methods=['GET', 'POST'])
def reset():
    form = ResetPassword()
    email = request.form.get("email")
    # Sending Password reset email
    if form.validate_on_submit():
        try:
            reset_email = auth.send_password_reset_email(email)
            flash('Un email vous a été envoyé sur votre boite mail afin de réinitialiser votre mot de passe !')
            return redirect(url_for('signin'))
        except:
            flash('Une erreur est survenue lors de la création de votre compte')
    return render_template("auth/reset_password.html", form=form)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """function for create an account"""
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
            auth.send_email_verification(user['idToken'])
            link = request.files.get('image', False)
            if link:
                storage.child(f'profile_pictures/{user["localId"]}').put(link)
            flash(
                'Votre compte a bien été créé, un email vous a été envoyé sur votre adresse mail !')
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
    """function for see your profile"""
    categories = db.child('categories').get().val()
    user = db.child('users').child(user_id()).get().val()
    link = storage.child(f"profile_pictures/{user_id()}").get_url(None)
    courses = dbc.collection(u'courses').where(
        u'created_by', u'==', user_id()).order_by(u'date', direction=firestore.Query.DESCENDING).get()
    try:
        storage.child(f"profile_pictures/{user_id()}").download('', 'image')
        os.remove('image')
        image_exist = True
    except:
        image_exist = False

    return render_template("profile/profile.html", user=user, image=link, image_exist=image_exist, courses=courses, user_id=user_id, categories=categories)

@app.route('/profile/courses', methods=['GET'])
@ensure_logged_in
def my_courses():
    """function for see your profile"""
    categories = db.child('categories').get().val()
    user = db.child('users').child(user_id()).get().val()
    link = storage.child(f"profile_pictures/{user_id()}").get_url(None)
    courses = dbc.collection(u'courses').where(
        u'created_by', u'==', user_id()).order_by(u'date', direction=firestore.Query.DESCENDING).get()


    return render_template("profile/my_courses.html", user=user, courses=courses, user_id=user_id, categories=categories)




@app.route('/profile/modify', methods=['GET', 'POST', 'PUT'])
@ensure_logged_in
def modify_profile():
    """function for modify your profile"""
    user = db.child('users').child(user_id()).get().val()
    form = ProfileForm()
    form.lastname.data = user['lastname']
    form.firstname.data = user['firstname']
    form.description.data = user['description']
    if form.validate_on_submit():
        try:
            db.child('users').child(user_id()).update({
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
    """function for delete your profile"""
    link = f'profile_pictures/{user_id()}'
    if request.method == "POST":
        bucket.blob(link).delete()
        db.child('users').child(user_id()).remove()
        user = auth.current_user['localId']
        auth_admin.delete_user(user)
        session.clear()
        flash("Votre compte a bien été supprimé.")
        return redirect(url_for('home'))
    return render_template("auth/delete.html")


@app.route('/course/create', methods=['GET', 'POST'])
@ensure_logged_in
def create_course():
    """function for create a course"""
    form = CourseForm()
    categories = db.child('categories').get().val()
    form.category.choices = categories
    if form.validate_on_submit():
        try:
            link = request.files.get('course', False)
            if link:
                ref = dbc.collection('courses').document()
                storage.child(
                    f'courses/{ref.id}').put(request.files['course'])
                ref.set({
                    u'title': request.form['title'],
                    u'resume': request.form['resume'],
                    u'category': request.form['category'],
                    u'created_by': user_id(),
                    u'date': datetime.datetime.utcnow(),
                    u'public': form.data.get('public')
                })

                flash('Votre cours un bien été créé')
                return redirect(url_for('my_courses'))

            else:
                form.course.errors = ['Ce champs est obligatoire !']
        except:
            flash(
                'Une erreur est survenue lors de la création de votre cours, veillez réessayer')

    return render_template("course/create_course.html", form=form)


@app.route('/course/delete/<id>', methods=['GET', 'POST'])
@ensure_logged_in
@is_my_course
def delete_course(id):
    """function for delete a course"""
    link = f'courses/{id}'
    if request.method == "POST":
        dbc.collection(u'courses').document(id).delete()
        bucket.blob(link).delete()
        flash("Votre fichier a bien été supprimé.")
        return redirect(url_for('my_courses'))
    return render_template("course/delete_course.html")


@app.route('/course/modify/<id>', methods=['GET', 'POST'])
@ensure_logged_in
@is_my_course
def modify_course(id):
    """function for modify a course"""
    course = dbc.collection(u'courses').document(id).get().to_dict()
    form = CourseForm()
    form.submit.data = "Modifier le cours"
    categories = db.child('categories').get().val()
    form.category.choices = categories
    form.title.data = course[u'title']
    form.resume.data = course[u'resume']
    form.category.data = course[u'category']
    form.public.data = course[u'public']
    if form.validate_on_submit():
        try:
            ref = dbc.collection('courses').document(id)
            link = request.files.get('course', False)
            if link:
                storage.child(
                    f'courses/{ref.id}').put(request.files['course'])['name']
            ref.update({
                u'title': request.form['title'],
                u'resume': request.form['resume'],
                u'category': request.form['category'],
                u'created_by': user_id(),
                u'date': datetime.datetime.utcnow(),
                u'public': form.data.get('public')
            })

            flash("Votre cours a bien été modifié.")
            return redirect(url_for('my_courses'))
        except:
            flash(
                'Une erreur est survenue lors de la modification de votre cours, veillez réessayer')
    return render_template("course/modify_course.html", form=form)


@app.route('/course/view/<id>', methods=['GET', 'POST'])
@ensure_logged_in
def view_course(id):
    """function for see a course"""
    course = dbc.collection('courses').document(id).get()
    return render_template("course/view_course.html", course=course)


@app.route('/profile/courses/<category>', methods=['GET', 'POST'])
@ensure_logged_in
def profile_courses_categories(category):
    """function for all your courses by category"""
    categories = db.child('categories').get().val()
    courses = dbc.collection(u'courses').where(u'created_by', u'==', user_id()).where(
        u'category', u'==', category).order_by(u'date', direction=firestore.Query.DESCENDING).get()

    return render_template(f"profile/courses_categories.html", courses=courses, category=category, categories=categories)


@app.route('/public/courses/', methods=['GET', 'POST'])
@ensure_logged_in
def public_courses():
    """function for all public courses"""
    categories = db.child('categories').get().val()
    courses = dbc.collection(u'courses').where(u'public', u'==', True).order_by(
        u'date', direction=firestore.Query.DESCENDING).get()

    return render_template(f"course/public_courses.html", courses=courses, categories=categories)


@app.route('/public/courses/<category>', methods=['GET', 'POST'])
@ensure_logged_in
def public_courses_categories(category):
    """function for all public courses by category"""
    categories = db.child('categories').get().val()
    courses = dbc.collection(u'courses').where(u'public', u'==', True).where(
        u'category', u'==', category).order_by(u'date', direction=firestore.Query.DESCENDING).get()

    return render_template(f"public/courses_categories.html", courses=courses, category=category, categories=categories)


@app.errorhandler(404)
def invalid_route(e):
    return render_template("error404.html")


if __name__ == "__main__":
    app.run(debug=True)
