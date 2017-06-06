from datetime import datetime
from functools import wraps
import json
import os
import re
from urllib.parse import urlparse, urlencode

from flask import Flask, redirect, request, Response, url_for
from flask_sqlalchemy import SQLAlchemy
import requests
from sqlalchemy.dialects.postgresql import ARRAY

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://eric:@localhost/pipet'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = '123'
db = SQLAlchemy(app)

ZENDESK_EMAIL = os.environ.get('ZENDESK_EMAIL')
ZENDESK_API_KEY = os.environ.get('ZENDESK_API_KEY')
ZENDESK_BASE_URL = 'https://{subdomain}.zendesk.com/api/v2'.format(subdomain=os.environ.get('ZENDESK_SUBDOMAIN'))
ZENDESK_AUTH = (ZENDESK_EMAIL + '/token', ZENDESK_API_KEY)

def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    return username == 'pipet' and password == app.secret_key


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


class Zendesk(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subdomain = db.Column(db.Text)
    admin_email = db.Column(db.Text)
    api_key = db.Column(db.Text)
    trigger_id = db.Column(db.Integer)
    target_id = db.Column(db.Integer)

    def create_target(self, webhook_url):
        target_payload = {'target': {
                'title': 'Pipet',
                'type': 'http_target',
                'active': True,
                'target_url': webhook_url,
                'username': 'pipet',
                'password': app.secret_key,
                'method': 'post',
                'content_type': 'application/json',}}
        resp = requests.post(ZENDESK_BASE_URL + '/targets.json', auth=ZENDESK_AUTH, json=target_payload)
        self.target_id = resp.json()['target']['id']

    def create_trigger(self):
        trigger_payload = {'trigger': {
            'actions': [
                {
                    'field': 'notification_target',
                    'value': [
                        str(self.target_id), '{"id": {{ticket.id}}}'
                    ]
                }
            ],
            'active': True,
            'conditions': {
                'all': [],
                'any': [
                    {'field': 'update_type', 'operator': 'is', 'value': 'Create'},
                    {'field': 'update_type', 'operator': 'is', 'value': 'Change'}
                ]
            },
            'description': None,
            'title': 'Pipet Ticket Trigger',
        }}

        resp = requests.post(ZENDESK_BASE_URL + '/triggers.json', auth=ZENDESK_AUTH, json=trigger_payload)
        self.trigger_id = resp.json()['trigger']['id']

    def destroy_target(self):
        requests.delete(ZENDESK_BASE_URL + '/targets/{id}.json'.format(id=self.target_id))
        self.target_id = None

    def destroy_trigger(self):
        requests.delete(ZENDESK_BASE_URL + '/triggers/{id}.json'.format(id=self.trigger_id))
        self.trigger_id = None


class ZendeskTicketComment(db.Model):
    """Cannot be deleted (unless ticket is deleted)"""
    id = db.Column(db.Integer, primary_key=True)
    zendesk_id = db.Column(db.Integer)
    created = db.Column(db.DateTime)
    body = db.Column(db.Text)
    public = db.Column(db.Boolean)
    ticket_id = db.Column(db.Integer, db.ForeignKey('zendesk_ticket.id'))
    author_id = db.Column(db.Integer, db.ForeignKey('zendesk_user.id'))

    ticket = db.relationship('ZendeskTicket', backref=db.backref('comments', lazy='dynamic'))
    author = db.relationship('ZendeskUser', backref=db.backref('comments', lazy='dynamic'))


class ZendeskUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    zendesk_id = db.Column(db.Integer)
    created = db.Column(db.DateTime)
    email = db.Column(db.Text)
    name = db.Column(db.Text)
    role = db.Column(db.Text)


class ZendeskGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    zendesk_id = db.Column(db.Integer)
    name = db.Column(db.Text)


class ZendeskTicket(db.Model):
    """Can be deleted by admins"""
    id = db.Column(db.Integer, primary_key=True)
    zendesk_id = db.Column(db.Integer)
    created = db.Column(db.DateTime)
    updated = db.Column(db.DateTime)
    type = db.Column(db.Text)
    subject = db.Column(db.Text)
    description = db.Column(db.Text)
    status = db.Column(db.Text)
    tags = db.Column(ARRAY(db.Text, dimensions=1))
    group_id = db.Column(db.Integer, db.ForeignKey('zendesk_group.id'))
    requester_id = db.Column(db.Integer, db.ForeignKey('zendesk_user.id'))

    group = db.relationship('ZendeskGroup', backref=db.backref('tickets', lazy='dynamic'))
    requester = db.relationship('ZendeskUser', backref=db.backref('tickets', lazy='dynamic'))

    def fetch_and_update(self):
        d = requests.get(ZENDESK_BASE_URL + '/tickets/{id}.json'.format(id=self.zendesk_id),
            auth=ZENDESK_AUTH).json()
        self.created = datetime.strptime(d['created_at'], '%Y-%m-%dT%H:%M:%SZ')
        self.updated = datetime.strptime(d['updated_at'], '%Y-%m-%dT%H:%M:%SZ')
        self.type = d['type']
        self.subject = d['subject']
        self.description = d['description']
        self.status = d['status']
        self.tags = sorted(d['tags'])

        requester = ZendeskUser.query.filter_by(zendesk_id=d['requester_id']).first()
        if requester:
            self.requester = requester
        else:
            rd = requests.get(ZENDESK_BASE_URL + '/users/{id}.json'.format(id=d['requester_id']), auth=ZENDESK_AUTH).json()
            self.requester = ZendeskUser(
                zendesk_id=d['requester_id'],
                created=datetime.strptime(rd['updated_at'], '%Y-%m-%dT%H:%M:%SZ'),
                email=rd['email'],
                name=rd['name'],
                role=rd['role'])

        group = ZendeskGroup.query.filter_by(zendesk_id=d['group_id']).first()
        if group:
            self.group = group
        else:
            gd = requests.get(ZENDESK_BASE_URL + '/groups/{id}.json'.format(id=d['group_id']), auth=ZENDESK_AUTH).json()
            self.group = ZendeskGroup(zendesk_id=d['group_id'], name=gd['name'])

    def fetch_comments(self):
        resp = requests.get(ZENDESK_BASE_URL + '/tickets/{ticket_id}/comments.json', auth=ZENDESK_AUTH)
        comments = []

        for d in resp.json()['comments']:
            if ZendeskTicketComment.query.filter_by(zendesk_id=d['id']).first():
                pass

            ztc = ZendeskTicketComment(
                zendesk_id=int(d['id']),
                created=datetime.strptime(d['created_at'], '%Y-%m-%dT%H:%M:%SZ'),
                body=d['body'],
                public=d['public'],
                ticket_id=self.ticket_id,
                author_id=d['author_id'])
            comments.append(ztc)

        return comments


@app.route('/')
def index():
    return 'Welcome to Pipet'


@app.route('/zendesk/auth')
def zendesk_auth():
    request_url = urlparse(request.url)
    params = [
        ('response_type', 'token'),
        ('client_id', 'postgres_export'),
        ('scope', 'targets:write targets:read tickets:write tickets:read triggers:write triggers:read'),
        ('redirect_uri', request_url.scheme + '://' + request_url.netloc + url_for('zendesk_callback')),]
    return redirect('https://sentry.zendesk.com/oauth/authorizations/new?' + urlencode(params))

@app.route('/zendesk/callback')
def zendesk_callback():
    r = requests.post(
        'https://sentry.zendesk.com/oauth/tokens',
        headers={'Content-Type': 'application/json'},
        json={"grant_type": "authorization_code", "code": request.args.get('code'),
        "client_id": "postgres_export", "client_secret": "56bead761c133a593fddfcc42484b19030e6629c7a4d5a8ae77e28e3c45c02e1",
        "redirect_uri": "http://localhost:5000/zendesk/callback", "scope": "tickets:read" })
    return str(r.json())

@app.route('/zendesk/install')
def zendesk_install():
    request_url = urlparse(request.url)
    domain = os.environ.get('DEV_DOMAIN') or request_url.netloc

    webhook_url = request_url.scheme + '://' + request_url.netloc + url_for('zendesk_hook')

    z = Zendesk()
    z.create_target(webhook_url)
    z.create_trigger()
    db.session.add(z)
    return redirect(url_for('index'))


@app.route('/zendesk/uninstall')
def zendesk_uninstall():
    request_url = urlparse(request.url)
    webhook_url = request_url.scheme + '://' + request_url.netloc + url_for('zendesk_hook')

    z = Zendesk.query.first()
    z.destroy_target()
    z.destroy_trigger()
    db.session.add(z)

    return redirect(url_for('index'))


@app.route("/zendesk/hook", methods=['POST'])
@requires_auth
def zendesk_hook():
    ticket_id = request.get_json()['id']
    ticket = ZendeskTicket.query.filter_by(zendesk_id=ticket_id).first()
    if not ticket:
        ticket = ZendeskTicket(zendesk_id=ticket_id)
    ticket.fetch_and_update()
    db.session.add(ticket)
    db.sesion.add(ticket.fetch_comments())

    return ('', 204)


if __name__ == "__main__":
    app.run()
