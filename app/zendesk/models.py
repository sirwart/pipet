from datetime import datetime
import os

from sqlalchemy.dialects.postgresql import ARRAY

from app import db


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
                'password': os.environ.get('FLASK_SECRET'),
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
            auth=ZENDESK_AUTH).json()['ticket']
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
            rd = requests.get(ZENDESK_BASE_URL + '/users/{id}.json'.format(id=d['requester_id']),
                auth=ZENDESK_AUTH).json()
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
            gd = requests.get(ZENDESK_BASE_URL + '/groups/{id}.json'.format(id=d['group_id']),
                auth=ZENDESK_AUTH).json()
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
