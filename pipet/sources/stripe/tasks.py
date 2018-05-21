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


def update(account, event_id=None):
    if not event_id:
        resp = account.get('/v1/events',
                           params={'starting_after': account.get_cursor('events')})
        resp.raise_for_status()
        data = resp.json()['data']
        if not data:
            # No additional events
            return
        else:
            event_id = data['id']
    # TODO do sync work


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
        while True:
            conn = session.connection()
            try:
                statements, cursor, has_more = cls.sync(account)
            except EmptyResponse:
                break

            for statement in statements:
                conn.execute(statement)

            session.commit()

            db.session.add(account)
            db.session.commit()

            if not has_more:
                break
