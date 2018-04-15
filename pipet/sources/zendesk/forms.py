from flask_wtf import FlaskForm
from wtforms import StringField, validators
from wtforms.fields import BooleanField
from wtforms.fields.html5 import EmailField


class CreateAccountForm(FlaskForm):
    subdomain = StringField('Subdomain', validators=[
                            validators.DataRequired()])
    admin_email = EmailField('Admin Email', validators=[
                             validators.DataRequired()])
    api_key = StringField('API Key', validators=[validators.DataRequired()])
    backfill = BooleanField('Backfill Zendesk data?')


class DestroyAccountForm(FlaskForm):
    drop = BooleanField('Drop tables from database?')
