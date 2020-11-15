from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, TextAreaField, PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length, EqualTo, Email
from wtforms.widgets import TextArea


class SigninForm(FlaskForm):
    email = StringField('Adresse mail', validators=[DataRequired(), Email()])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    remember_me = BooleanField('Se souvenir de moi')
    submit = SubmitField('Se connecter')


class SignupForm(FlaskForm):
    email = StringField('Adresse mail', validators=[DataRequired(), Email()])
    password = PasswordField('Mot de passe', validators=[
        DataRequired(),
        Length(min=6, max=20)
    ])
    lastname = StringField('Votre nom', validators=[DataRequired()])
    firstname = StringField('Votre prénom', validators=[DataRequired()])
    description = StringField(
        'Votre description', widget=TextArea(), validators=[Length(max=256)])
    image = FileField('Votre image de profile', validators=[
        FileAllowed(['jpg', 'png'], 'Image uniquement !')
    ])
    submit = SubmitField('Créer le compte')


class ProfileForm(FlaskForm):
    lastname = StringField('Votre nom', validators=[DataRequired()])
    firstname = StringField('Votre prénom', validators=[DataRequired()])
    description = StringField(
        'Votre description', widget=TextArea(), validators=[Length(max=256)])
    image = FileField('Votre image de profile', validators=[
        FileAllowed(['jpg', 'png'], 'Image uniquement !')
    ])
    submit = SubmitField('Modifier mon compte')


class CourseForm(FlaskForm):
    title = StringField('Le titre de votre cours', validators=[DataRequired()])
    resume = StringField('Un petit résumé',  widget=TextArea(), validators=[
                         DataRequired(), Length(max=256)])
    course = FileField('Votre cours', validators=[
        FileAllowed(
            ['pdf'], 'Pdf uniquement !')
    ])
    category = SelectField('Catégorie', choices=[])
    public = BooleanField(
        'Voulez vous rendre public ce cours ?', default=True,
        render_kw={'checked': ''})
    submit = SubmitField('Ajouter le cours')


class ResetPasswordForm(FlaskForm):
    email = StringField('Adresse mail', validators=[DataRequired(), Email()])
    submit = SubmitField('Envoyer le mail')


class SearchForm(FlaskForm):
    search = StringField(
        'Recherche par rapport à la description d\'un cours', [DataRequired()])
    submit = SubmitField('Rechercher')


class CommentForm(FlaskForm):
    body = StringField('Votre commentaire',  widget=TextArea(), validators=[
        DataRequired(), Length(max=256)])
    submit = SubmitField("Envoyer votre commentaire")
