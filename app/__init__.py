import json
import os

from flask import Flask
from flask_login import current_user, LoginManager, UserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
import sqlalchemy
from sqlalchemy.schema import CreateSchema, DropSchema
from wtforms import StringField
from wtforms.validators import Required


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://eric:@localhost/pipet'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('FLASK_SECRET_KEY')

login_manager = LoginManager(app)
login_manager.login_view = "login"

db = SQLAlchemy(app)

schemas = []
tables = []

# import app.admin as admin_blueprint
# app.register_blueprint(admin_blueprint.app)
# for name in admin_blueprint.models.TABLES:
#     tables.append(admin_blueprint.models.TABLES.get(name))


import app.zendesk as zendesk_blueprint
app.register_blueprint(zendesk_blueprint.app, url_prefix='/zendesk')
schemas.append(zendesk_blueprint.models.SCHEMANAME)
for name in zendesk_blueprint.models.TABLES:
    if name == '_sa_module_registry':
        continue
    tables.append(zendesk_blueprint.models.TABLES.get(name))


import app.stripe as stripe_blueprint
app.register_blueprint(stripe_blueprint.stripe, url_prefix='/stripe')
schemas.append(stripe_blueprint.models.SCHEMANAME)
for name in stripe_blueprint.models.TABLES:
    if name == '_sa_module_registry':
        continue
    tables.append(stripe_blueprint.models.TABLES.get(name))


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)


class LoginForm(FlaskForm):
    name = StringField(validators=[Required()])


@app.route('/')
def index():
    return "Welcome to Pipet"


@app.route('/login', methods=('GET', 'POST'))
def login():
    form = LoginForm()
    if form.validate_on_submit():
        return redirect(request.args.get("next") or url_for("index"))
    return "login page"


# Setup Scripts
def create_schema():
    for schema in app.blueprints:
        db.session.execute(CreateSchema(schema))
    db.session.commit()


def drop_schema():
    for schema in app.blueprints:
        db.session.execute(DropSchema(schema))
    db.session.commit()


def create_tables():
    for table in tables:
        table.metadata.create_all(db.engine)


def drop_tables():
    for table in tables:
        table.metadata.drop_all(db.engine)
