from flask import url_for
import requests
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.schema import DDL

from pipet.models import db
from pipet.sources.zendesk.models import Base, SCHEMANAME


class ZendeskAccount(db.Model):
    subdomain = db.Column(db.Text)
    admin_email = db.Column(db.Text)
    api_key = db.Column(db.Text)
    # has the database schema and tables been created
    initialized = db.Column(db.Boolean)
    cursors = db.Column(JSON, default=lambda: {})

    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'))

    organization = db.relationship('Organization', backref=db.backref(
        'zendesk_account', lazy=True, uselist=False))

    @property
    def base_url(self):
        return 'https://{subdomain}.zendesk.com'.format(subdomain=self.subdomain)

    @property
    def auth(self):
        return self.admin_email + '/token', self.api_key

    def get(self, path, **kwargs):
        kwargs['url'] = self.base_url + path
        kwargs['auth'] = account.auth
        return requests.get(**kwargs)

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
