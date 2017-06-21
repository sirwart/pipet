from functools import wraps
import os

from flask import Blueprint, redirect, request, Response, render_template, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
import requests
from wtforms import StringField, validators
from wtforms.fields.html5 import EmailField

from pipet import engine, session
from .models import (
    SCHEMANAME,
    ZENDESK_MODELS,
    Account,
    Group,
    Ticket,
    TicketComment,
    User,
)


app = Blueprint(SCHEMANAME, __name__, template_folder='templates')


def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    return username == 'pipet' and password == os.environ.get('FLASK_SECRET')


def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


class AccountForm(FlaskForm):
    subdomain = StringField('Subdomain', validators=[validators.DataRequired()])
    admin_email = EmailField('Admin Email', validators=[validators.DataRequired()])
    api_key = StringField('API Key', validators=[validators.DataRequired()])


@app.route('/')
@login_required
def index():
    return "Zendesk Pipet"


@app.route('/activate', methods=['GET', 'POST'])
@login_required
def activate():
    form = AccountForm()
    if form.validate_on_submit():
        account = Account(
            subdomain=form.subdomain.data,
            admin_email=form.admin_email.data,
            api_key=form.api_key.data,
            workspace_id=current_user.id)
        # account.create_target()
        # account.create_trigger()
        session.add(account)
        session.commit()
        return redirect(url_for('index'))
    return render_template('activate.html', form=form)


@app.route('/deactivate')
def deactivate():
    z = Account.query.filter(user=current_user)
    z.destroy_target()
    z.destroy_trigger()
    session.add(z)
    return redirect(url_for('index'))


@app.route("/hook", methods=['POST'])
@requires_auth
def hook():
    ticket_id = request.get_json()['id']
    resp = requests.get(current_user.account.api_base_url + \
        '/tickets/{id}.json?include=users,groups'.format(id=ticket_id),
        auth=current_user.account.auth)
    
    ticket, _ = Ticket.get_or_insert(resp.json()['ticket'])
    session.add(ticket)
    session.add_all(ticket.update(resp.json()))

    resp = requests.get(current_user.account.api_base_url + \
        '/tickets/{id}/comments.json'.format(id=current_user.id), auth=current_user.account.auth)
    sesion.add_all(ticket.update_comments(resp.json()['comments']))
    return ('', 204)
