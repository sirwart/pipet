from flask import redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user, LoginManager
from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, validators
from wtforms.fields.html5 import EmailField

from pipet import app, session, engine
from pipet.models import Workspace

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(workspace_id):
    return session.query(Workspace).get(workspace_id)


class SignupForm(FlaskForm):
    email = EmailField('Email', validators=[validators.DataRequired()])
    password = PasswordField('Password', validators=[validators.DataRequired()])


class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[validators.DataRequired()])
    password = PasswordField('Password', validators=[validators.DataRequired()])


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/signup', methods=('GET', 'POST'))
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        user = Workspace(form.email.data, form.password.data)
        session.add(user)
        session.commit()
        return redirect(url_for("index"))
    return render_template('signup.html', form=form)


@app.route('/login', methods=('GET', 'POST'))
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = session.query(Workspace).filter_by(email=form.email.data).first()
        if user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for("index"))
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))
