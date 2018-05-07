from flask_wtf import FlaskForm
from wtforms import StringField, validators
from wtforms.fields.html5 import EmailField


class CreateAccountForm(FlaskForm):
    api_key = StringField('API Key', validators=[validators.DataRequired()])
