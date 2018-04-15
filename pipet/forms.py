from flask_wtf import FlaskForm
from wtforms import StringField, validators
from wtforms.fields.html5 import EmailField


class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[validators.DataRequired('Email required.'),
                                            validators.Email('You must enter a valid email.')])


class OrganizationForm(FlaskForm):
    name = StringField('name', validators=[validators.DataRequired()])
    database_credentials = StringField('Database Credentials', validators=[
                                       validators.DataRequired()])
