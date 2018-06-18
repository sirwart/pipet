from inspect import isclass

from celery_once import QueueOnce
import requests
import stripe

from pipet import celery, db
from pipet.sources.stripe import StripeAccount
from pipet.sources.stripe.models import (
    Base,
    CLASS_REGISTRY,
    EmptyResponse,
)


@celery.task(base=QueueOnce)
def sync(account_id):
    # backfill or update
    pass


def get_class_for_object_type(object_type):
    try:
        return [m for n, m in CLASS_REGISTRY.items() if isclass(m) and issubclass(m, Base) and object_type == m.object_type()][0]
    except IndexError:
        raise ValueError(
            'No matching class found for object %s ' % object_type)


def update(account, event_id=None):
    """
    All Stripe models have an `object_type` attribute
    For each event in the response, find the model from the `object` within the `data` attribute,
    and based on the `object` type, upsert the object.
    """
    event_id = event_id or account.event_id
    assert event_id is not None

    statements = []

    while True:
        resp = account.get('/v1/events',
                           params={'starting_after': event_id})
        resp.raise_for_status()
        data = resp.json()['data']

        for event_object in [d['data']['object'] for d in data]:
            try:
                cls = get_class_for_object_type(event_object['object'])
            except ValueError:
                continue
            statements.append(cls.upsert(cls.parse(event_object)))

        if len(data):
            event_id = data[-1]['id']
        else:
            break

        if not data['has_more']:
            break

    for statement in statements:
        conn.execute(statement)
    session.commit()

    account.event_id = event_id
    db.session.add(account)
    db.session.commit()


def backfill(account):
    """
    TODO https://www.ehfeng.com/mirroring-stripe/
    """
    resp = account.get('/v1/events', params={'limit': 1})
    resp.raise_for_status()
    event_id = resp.json()['data'][0]['id']

    account = StripeAccount.query.get(account_id)
    session = account.organization.create_session()

    for cls in [m for n, m in CLASS_REGISTRY.items() if isclass(m) and issubclass(m, Base) and m.endpoint]:
        # TODO Make these parallel to speed up execution
        cursor = None
        while True:
            conn = session.connection()
            try:
                statements, cursor, has_more = cls.sync(account, cursor)
            except EmptyResponse:
                break

            for statement in statements:
                conn.execute(statement)

            session.commit()

            if not has_more:
                break

    account.backfilled = True
    account.event_id = event_id
    db.session.add(account)
    db.session.commit()

    update(account)
