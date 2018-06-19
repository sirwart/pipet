from inspect import isclass
import logging

import requests
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.schema import DDL

from pipet.models import db
from pipet.sources.stripe.models import (
    Base,
    CLASS_REGISTRY,
    EmptyResponse,
    SCHEMANAME,
    STRIPE_API_VERSION,
)


def get_class_for_object_type(object_type):
    try:
        return [m for n, m in CLASS_REGISTRY.items() if isclass(m) and issubclass(m, Base) and object_type == m.object_type()][0]
    except IndexError:
        raise ValueError(
            'No matching class found for object %s ' % object_type)


class StripeAccount(db.Model):
    api_key = db.Column(db.Text)
    initialized = db.Column(db.Boolean)
    backfilled = db.Column(db.Boolean)
    event_id = db.Column(db.Text)

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
        kwargs['params'] = kwargs.get('params', {})
        kwargs['params']['limit'] = kwargs['params'].get('limit', 100)
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

    def update(self, event_id=None):
        """
        All Stripe models have an `object_type` attribute
        For each event in the response, find the model from the `object` within the `data` attribute,
        and based on the `object` type, upsert the object.
        """
        logging.info('Starting update for <StripeAccount {}>'.format(self.id))
        event_id = event_id or self.event_id

        statements = []
        session = self.organization.create_session()

        while True:
            conn = session.connection()
            resp = self.get('/v1/events',
                            params={'ending_before': event_id})
            resp.raise_for_status()
            data = resp.json()['data']

            for event_object in [d['data']['object'] for d in data]:
                try:
                    cls = get_class_for_object_type(event_object['object'])
                except ValueError:
                    continue
                statements.append(cls.upsert(cls.parse(event_object)))

            if len(data):
                event_id = data[0]['id']
            else:
                break

            if not resp.json()['has_more']:
                break

        for statement in statements:
            conn.execute(statement)
        session.commit()

        self.event_id = event_id
        db.session.add(self)
        db.session.commit()

    def backfill(self):
        """
        TODO https://www.ehfeng.com/mirroring-stripe/
        """
        logging.info(
            'Starting backfill for <StripeAccount {}>'.format(self.id))

        # Get latests event_id. Iterating is faster than allowing the
        # update function to attempt to upsert.
        event_id = None
        while True:
            resp = self.get('/v1/events',
                            params={'starting_after': event_id})

            if resp.json()['data']:
                event_id = resp.json()['data'][-1]['id']
            else:
                break

            if not resp.json()['has_more']:
                break

        # Start Backfill
        session = self.organization.create_session()

        for cls in [m for n, m in CLASS_REGISTRY.items() if isclass(m) and issubclass(m, Base) and m.endpoint]:
            # TODO Make these parallel to speed up execution
            logging.info('Backfilling for <StripeAccount {}>, class {}'.format(
                self.id, cls.__name__))
            cursor = None
            while True:
                conn = session.connection()
                try:
                    statements, cursor, has_more = cls.sync(self, cursor)
                except EmptyResponse:
                    break

                for statement in statements:
                    conn.execute(statement)

                session.commit()

                if not has_more:
                    break

        self.backfilled = True
        db.session.add(self)
        db.session.commit()

        self.update(event_id)
