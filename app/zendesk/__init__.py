from functools import wraps
import os

from flask import Blueprint, redirect, request, Response, render_template, url_for
from flask_login import login_required
import requests

from app import db, login_manager
from app.zendesk.models import Zendesk, ZendeskGroup, ZendeskTicket, ZendeskTicketComment, ZendeskUser


zendesk = Blueprint('zendesk', __name__, template_folder='templates')

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


@zendesk.route('/')
@login_required
def index():
    return "Pipet Zendesk"


@zendesk.route('/activate')
def activate():
    webhook_url = os.environ.get('PIPET_DOMAIN') + url_for('zendesk_hook')

    z = Zendesk()
    z.create_target(webhook_url)
    z.create_trigger()
    db.session.add(z)
    return redirect(url_for('index'))


@zendesk.route('/deactivate')
def deactivate():
    request_url = urlparse(request.url)
    webhook_url = request_url.scheme + '://' + request_url.netloc + url_for('zendesk_hook')

    z = Zendesk.query.first()
    z.destroy_target()
    z.destroy_trigger()
    db.session.add(z)

    return redirect(url_for('index'))


@zendesk.route("/hook", methods=['POST'])
@requires_auth
def hook():
    ticket_id = request.get_json()['id']
    ticket = ZendeskTicket.query.filter_by(zendesk_id=ticket_id).first()
    if not ticket:
        ticket = ZendeskTicket(zendesk_id=ticket_id)
    ticket.fetch_and_update()
    db.session.add(ticket)
    db.sesion.add(ticket.fetch_comments())
    return ('', 204)
