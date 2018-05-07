import requests
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.schema import DDL

from pipet.models import db
from pipet.sources.stripe.models import (
    Base,
    SCHEMANAME,
    STRIPE_API_VERSION,
)


class StripeAccount(db.Model):
    api_key = db.Column(db.Text)
    initialized = db.Column(db.Boolean)
    cursors = db.Column(JSON, default=lambda: {})

    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'))

    organization = db.relationship('Organization', backref=db.backref(
        'stripe_account', lazy=True, uselist=False))

    @property
    def auth(self):
        return self.api_key, None

    def get(self, path, **kwargs):
        kwargs['headers'] = kwargs.get('headers', {}).update(
            {'Stripe-Version': STRIPE_API_VERSION})
        kwargs['auth'] = self.auth
        kwargs['params'] = kwargs.get('params', {}).update({'limit': 100})
        return requests.get('https://api.stripe.com' + path, **kwargs)

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
