import os
import firebase_admin
import pyrebase
import json
import datetime
from functools import wraps
from firebase_admin import credentials, auth as auth_admin, firestore
from flask import Flask, render_template, url_for, flash, request, session, redirect, abort
from flask_wtf.csrf import CSRFProtect
from app.forms import SigninForm, SignupForm, ProfileForm, CourseForm, ResetPasswordForm, SearchForm, CommentForm
from google.cloud import storage as storage_cloud
from flask import Blueprint
from flask_paginate import Pagination, get_page_parameter, get_page_args


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


def user_id():
    if session.get('user'):
        return session.get('user')['localId']


def get_pdf(id_course):
    return storage.child(f"courses/{id_course}").get_url(None)


def get_img(id_user):
    try:
        storage.child(f"profile_pictures/{id_user}").download('', 'image')
        os.remove('image')
        return storage.child(f"profile_pictures/{id_user}").get_url(None)
    except:
        return '/static/images/profile.jpg'


def get_created_by_name(id):
    user = db.child('users').child(id).get().val()

    if user != None:
        return user['firstname'] + ' ' + user['lastname']
    else:
        return 'Utilisateur supprimé'


def is_admin():
    user_type = db.child('users').child(
        user_id()).child('userType').get().val()
    if user_type == 'ADMIN':
        return True
    else:
        return False


def is_mine(id):
    if id == session.get('user')['localId']:
        return True
    else:
        return False


app.jinja_env.globals.update(
    get_pdf=get_pdf, is_mine=is_mine, get_created_by_name=get_created_by_name, is_admin=is_admin, get_img=get_img)


@app.errorhandler(404)
def invalid_route(e):
    return render_template("error404.html")


def ensure_logged_in(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('user'):
            flash("Connecte toi pour pouvoir accéder à cette page")
            return redirect(url_for('signin', next=request.url))
        return fn(*args, **kwargs)
    return wrapper


def is_public(fn):
    @wraps(fn)
    def wrapper(id, *args, **kwargs):
        course_json = dbc.collection('courses').document(id).get()
        course = course_json.to_dict()
        if is_admin() == False:
            if course['public'] != True:
                if user_id() != course['created_by']:
                    flash("Ce cours n'est pas public !")
                    return redirect(url_for('profile'))
        return fn(id, *args, **kwargs)
    return wrapper


def have_access_course(fn):
    @wraps(fn)
    def wrapper(id, *args, **kwargs):
        course_json = dbc.collection('courses').document(id).get()
        course = course_json.to_dict()
        if is_admin() == False:
            if course['created_by'] != user_id():
                flash("Ce n'est pas l'un de vos cours !")
                return redirect(url_for('profile'))
        return fn(id, *args, **kwargs)
    return wrapper


def have_access_comment(fn):
    @wraps(fn)
    def wrapper(id, *args, **kwargs):
        comment_json = dbc.collection('comments').document(id).get()
        comment = comment_json.to_dict()
        if is_admin() == False:
            if comment['created_by'] != user_id():
                flash("Ce n'est pas l'un de vos commentaires !")
                return redirect(url_for('profile'))
        return fn(id, *args, **kwargs)
    return wrapper


def have_access_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user_type = db.child('users').child(
            user_id()).child('userType').get().val()
        if user_type != 'ADMIN':
            flash("Vous n'avez pas accès à cette partie !")
            return redirect(url_for('profile'))
        return fn(*args, **kwargs)
    return wrapper


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
    form = ResetPasswordForm()
    email = request.form.get("email")
    # Sending Password reset email
    if form.validate_on_submit():
        try:
            reset_email = auth.send_password_reset_email(email)
            flash(
                'Un email vous a été envoyé sur votre boite mail afin de réinitialiser votre mot de passe !')
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
        if request.form['password'] != request.form['confirm_password']:
            form.confirm_password.errors = [
                'Les mots de passes ne sont pas identiques']
        else:
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
                    storage.child(
                        f'profile_pictures/{user["localId"]}').put(link)
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
    user = db.child('users').child(user_id()).get().val()
    link = storage.child(f"profile_pictures/{user_id()}").get_url(None)
    try:
        storage.child(f"profile_pictures/{user_id()}").download('', 'image')
        os.remove('image')
        image_exist = True
    except:
        image_exist = False

    return render_template("profile/profile.html", user=user, image=link, image_exist=image_exist, user_id=user_id)


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


@app.route('/profile/delete', methods=['GET', 'POST'])
@ensure_logged_in
def delete_profile():
    """function for delete your profile"""
    link = f'profile_pictures/{user_id()}'
    if request.method == "POST":
        comments = dbc.collection(u'comments').where(u'created_by', u'==', user_id(
        )).get()
        comment_ids = []
        for i in comments:
            comment_ids.append(i.id)
        for i in comment_ids:
            dbc.collection(u'comments').document(i).delete()
        try:
            storage.child(
                f"profile_pictures/{user_id()}").download('', 'image')
            os.remove('image')
            bucket.blob(link).delete()
        except:
            pass

        db.child('users').child(user_id()).remove()
        user = auth.current_user['localId']
        auth_admin.delete_user(user)
        session.clear()

        flash("Votre compte a bien été supprimé.")
        return redirect(url_for('profile'))
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
                return redirect(url_for('courses', privacy='private', category='all'))

            else:
                form.course.errors = ['Ce champ est obligatoire !']
        except:
            flash(
                'Une erreur est survenue lors de la création de votre cours, veillez réessayer')

    return render_template("course/create_course.html", form=form)


@app.route('/courses/<privacy>/<category>', methods=['GET', 'POST'])
@ensure_logged_in
def courses(privacy, category):
    form = SearchForm()

    q = ''
    if request.method == "POST":
        q = request.form['search']

    search = False
    """function for see your profile"""
    categories = db.child('categories').get().val()
    user = db.child('users').child(user_id()).get().val()
    if privacy == 'private':
        courses = dbc.collection(u'courses').where(u'created_by', u'==', user_id(
        )).order_by(u'date', direction=firestore.Query.DESCENDING)
    elif privacy == 'public':
        courses = dbc.collection(u'courses').where(u'public', u'==', True).order_by(
            u'date', direction=firestore.Query.DESCENDING)
    else:
        abort(404)

    if category != 'all':
        check_category_exist = False
        i = 0
        while i < len(categories) and check_category_exist == False:
            if categories[i] == category:
                check_category_exist = True
            i += 1
        if check_category_exist == False:
            abort(404)

        courses = courses.where(u'category', u'==', category)

    courses = courses.get()
    if q != '':
        search_course = list()
        for course in courses:
            course_dict = course.to_dict()
            if course_dict['resume'].lower().__contains__(q.lower()):
                search_course.append(course)
        courses = search_course
    #   PAGINATION
    page, per_page, offset = get_page_args(page_parameter='page',
                                           per_page_parameter='per_page')
    total = len(courses)
    courses_page = courses[offset: offset + per_page]
    pagination_courses = courses_page
    pagination = Pagination(page=page, per_page=per_page,
                            total=total, css_framework='bootstrap4')
#   PAGINATION

    return render_template("course/courses.html", courses=pagination_courses, categories=categories,  page=page, per_page=per_page, pagination=pagination, privacy=privacy, category=category, form=form)


@app.route('/course/delete/<id>', methods=['GET', 'POST'])
@ensure_logged_in
@have_access_course
def delete_course(id):
    """function for delete a course"""
    link = f'courses/{id}'
    if request.method == "POST":
        dbc.collection(u'courses').document(id).delete()
        bucket.blob(link).delete()
        flash("Votre fichier a bien été supprimé.")
        return redirect(url_for('courses', privacy='private', category='all'))
    return render_template("course/delete_course.html")


@app.route('/course/modify/<id>', methods=['GET', 'POST'])
@ensure_logged_in
@have_access_course
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
            return redirect(url_for('courses', privacy='private', category='all'))
        except:
            flash(
                'Une erreur est survenue lors de la modification de votre cours, veillez réessayer')
    return render_template("course/modify_course.html", form=form)


@app.route('/course/view/<id>', methods=['GET', 'POST'])
@ensure_logged_in
@is_public
def view_course(id):
    form = CommentForm()
    """function for see a course"""
    course = dbc.collection('courses').document(id).get()
    comments = dbc.collection(u'comments').where(u'idCourse', u'==', id).order_by(
        u'date', direction=firestore.Query.DESCENDING).get()

    if form.validate_on_submit():
        try:
            ref = dbc.collection('comments').document()
            ref.set({
                u'text': request.form['body'],
                u'created_by': user_id(),
                u'date': datetime.datetime.utcnow(),
                u'idCourse': id
            })
            flash('Votre commentaire un bien été créé')
            return redirect(request.url)
        except:
            flash(
                'Une erreur est survenue lors de la création de votre commentaire, veillez réessayer')
    return render_template("course/view_course.html", course=course, form=form, comments=comments)


@app.route('/delete_comment/<id>', methods=['GET', 'POST'])
@ensure_logged_in
@have_access_comment
def delete_comment(id):
    if request.method == "POST":
        dbc.collection('comments').document(id).delete()
        flash('Votre commentaire un bien été supprimé')
        return redirect(request.referrer)
    return redirect(url_for('courses', privacy='private', category='all'))


@app.route('/modify_comment/<id>', methods=['GET', 'POST'])
@ensure_logged_in
@have_access_comment
def modify_comment(id):
    comments = dbc.collection(u'comments').document(id).get().to_dict()
    form = CommentForm()
    form.submit.data = "Modifier le commentaire"
    form.body.data = comments[u'text']
    if form.validate_on_submit():
        try:
            ref = dbc.collection('comments').document(id)
            ref.update({
                u'text': request.form['body']
            })
            flash("Votre commentaire a bien été modifié.")
            return redirect(url_for('profile'))
        except:
            flash(
                'Une erreur est survenue lors de la modification de votre commentaire, veillez réessayer')

    return render_template("comment/modify_comment.html", form=form)


@app.route('/admin/categories', methods=['GET', 'POST'])
@ensure_logged_in
@have_access_admin
def admin_categories():
    """"""
    categories = db.child('categories').get().val()
    return render_template("admin/categories.html", categories=categories)


@app.route('/admin/delete', methods=['POST'])
@ensure_logged_in
@have_access_admin
def delete_category():
    if request.method == "POST":
        category = request.form.get('delete')
        categories = db.child('categories').get().val()
        categories.remove(category)
        db.child('categories').set(categories)

    return render_template("admin/categories.html", categories=categories)


@app.route('/admin/modify', methods=['POST'])
@ensure_logged_in
@have_access_admin
def modify_category():
    if request.method == "POST":
        modify = request.form.get('modify')
        category = request.form.get('category')
        categories = db.child('categories').get().val()
        categories.remove(category)
        categories.append(modify)
        db.child('categories').set(categories)
        categories = dbc.collection(u'courses').where(
            u'category', u'==', category).get()
        for category in categories:
            category_id = category.id
            dbc.collection(u'courses').document(category_id).update({
                u'category': modify
            })
        categories = db.child('categories').get().val()
    return render_template("admin/categories.html", categories=categories)


@app.route('/admin/create', methods=['POST'])
@ensure_logged_in
@have_access_admin
def create_category():
    categories = db.child('categories').get().val()
    if request.method == "POST":
        create_category = request.form.get('create')
        categories.append(create_category)
        db.child('categories').set([create_category])

    return render_template("admin/categories.html", categories=categories)


if __name__ == "__main__":
    app.run(debug=True)
