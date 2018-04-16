from flask import url_for
import requests
from sqlalchemy import create_engine
from sqlalchemy.schema import DDL

from pipet.models import db
from pipet.sources.zendesk.models import Base, SCHEMANAME


class ZendeskAccount(db.Model):
    subdomain = db.Column(db.Text)
    admin_email = db.Column(db.Text)
    api_key = db.Column(db.Text)
    trigger_id = db.Column(db.Text)
    target_id = db.Column(db.Text)
    # has the database schema and tables been created
    initialized = db.Column(db.Boolean)

    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'))

    organization = db.relationship('Organization', backref=db.backref(
        'zendesk_account', lazy=True, uselist=False))

    @property
    def base_url(self):
        return 'https://{subdomain}.zendesk.com/api/v2'.format(subdomain=self.subdomain)

    @property
    def auth(self):
        return (self.admin_email + '/token', self.api_key)

    @property
    def target_exists(self):
        resp = requests.get(
            self.base_url + '/targets/{id}.json'.format(id=self.target_id))
        if resp.status_code == 200:
            return True
        return False

    @property
    def trigger_exists(self):
        resp = requests.get(
            self.base_url + '/triggers/{id}.json'.format(id=self.target_id))
        if resp.status_code == 200:
            return True
        return False

    def create_target(self):
        """Returns True if target was created, False if it already existed"""
        resp = requests.get(self.base_url + '/targets.json', auth=self.auth)
        for target in resp.json()['targets']:
            if target['type'] == 'url_target_v2' and target['target_url'] == url_for('zendesk.hook', _external=True):
                self.target_id = target['id']
                return False

        if self.target_id and requests.get(self.base_url + '/targets/{id}.json'.format(id=self.target_id), auth=self.auth).status_code == 200:
            return False

        target_payload = {'target': {
            'title': 'Pipet',
            'type': 'http_target',
            'active': True,
            'target_url': url_for('zendesk.hook', _external=True),
            'username': self.subdomain,
            'password': self.api_key,
            'method': 'post',
            'content_type': 'application/json', }}
        resp = requests.post(self.base_url + '/targets.json',
                             auth=self.auth, json=target_payload)
        assert resp.status_code == 201
        self.target_id = resp.json()['target']['id']
        return True

    def create_trigger(self):
        for trigger in requests.get(self.base_url + '/triggers.json', auth=self.auth).json()['triggers']:
            if sum([1 for action in trigger['actions'] if action['field'] == 'notification_target' and action['value'][0] == str(self.target_id)]) > 0:
                self.trigger_id = trigger['id']
                return False

        if self.trigger_id and requests.get(self.base_url + '/triggers/{id}.json'.format(id=self.trigger_id), auth=self.auth).status_code == 200:
            return False

        trigger_payload = {'trigger': {
            'actions': [{
                'field': 'notification_target',
                'value': [str(self.target_id), '{"id": {{ticket.id}}}']
            }],
            'active': True,
            'conditions': {
                'all': [],
                'any': [
                    {'field': 'update_type', 'operator': 'is', 'value': 'Create'},
                    {'field': 'update_type', 'operator': 'is', 'value': 'Change'}
                ]
            },
            'description': None,
            'title': 'Pipet Trigger',
        }}

        resp = requests.post(self.base_url + '/triggers.json',
                             auth=self.auth, json=trigger_payload)
        self.trigger_id = resp.json()['trigger']['id']
        return True

    def destroy_target(self):
        requests.delete(self.base_url + '/targets/{id}.json'.format(id=self.target_id),
                        auth=self.auth)
        self.target_id = None

    def destroy_trigger(self):
        requests.delete(self.base_url + '/triggers/{id}.json'.format(id=self.trigger_id),
                        auth=self.auth)
        self.trigger_id = None

    def create_all(self, session):
        session.bind.execute(
            DDL('CREATE SCHEMA IF NOT EXISTS {schema}'.format(schema=SCHEMANAME)))
        Base.metadata.create_all(session.bind)
        self.initialized = True

    def drop_all(self, session):
        Base.metadata.drop_all(session.bind)
        session.bind.execute(
            DDL('DROP SCHEMA IF EXISTS {schema}'.format(schema=SCHEMANAME)))
        self.initialized = False
