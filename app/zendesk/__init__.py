from functools import wraps
import os

from flask import Blueprint, redirect, request, Response, render_template, url_for
from flask_login import login_required
import requests

from app import db, login_manager
from app.zendesk.models import (
    Account,
    Group,
    Ticket,
    TicketComment,
    User,
    SCHEMANAME
)


app = Blueprint(SCHEMANAME, __name__, template_folder='templates')

ZENDESK_EMAIL = os.environ.get('ZENDESK_EMAIL')
ZENDESK_API_KEY = os.environ.get('ZENDESK_API_KEY')
ZENDESK_BASE_URL = 'https://{subdomain}.zendesk.com/api/v2'.format(subdomain=os.environ.get('ZENDESK_SUBDOMAIN'))
ZENDESK_AUTH = (ZENDESK_EMAIL + '/token', ZENDESK_API_KEY)

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


@app.route('/')
@login_required
def index():
    return "Pipet Zendesk"


@app.route('/activate')
def activate():
    z = Account()
    z.create_target()
    z.create_trigger()
    db.session.add(z)
    return redirect(url_for('index'))


@app.route('/deactivate')
def deactivate():
    z = Account.query.filter(user=current_user)
    z.destroy_target()
    z.destroy_trigger()
    db.session.add(z)
    return redirect(url_for('index'))


@app.route("/hook", methods=['POST'])
@requires_auth
def hook():
    ticket_id = request.get_json()['id']
    ticket = Ticket.query.get(ticket_id)
    if not ticket:
        ticket = Ticket(id=ticket_id)
    db.session.add(ticket.update())
    db.sesion.add(ticket.update_comments())
    return ('', 204)
