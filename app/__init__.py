import json
import os

from flask import Flask
from flask_login import LoginManager, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import Form, fields, validators, Required

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://eric:@localhost/pipet'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = '123'

login_manager = LoginManager(app)
login_manager.login_view = "login"

db = SQLAlchemy(app)

from app.admin import admin
app.register_blueprint(admin)

from app.zendesk import zendesk
app.register_blueprint(zendesk, url_prefix='/zendesk')


class User(UserMixin, db.Model):
	id = db.Column(db.Integer, primary_key=True)


class LoginForm(Form):
	name = fields.TextField(validators=[Required()])

@app.route('/')
def index():
    return "Welcome to Pipet"


@app.route('/login', methods=('GET', 'POST'))
def login():
	form = LoginForm()
	if form.validate_on_submit():
		return redirect(request.args.get("next") or url_for("index"))
	return "login page"
