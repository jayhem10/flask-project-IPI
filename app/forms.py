from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, TextAreaField, PasswordField, BooleanField, SubmitField
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
