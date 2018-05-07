from celery_once import QueueOnce
from inspect import isclass
from sqlalchemy.orm.attributes import flag_modified
import stripe
import requests

from pipet import celery, db
from pipet.sources.stripe import StripeAccount
from pipet.sources.stripe.models import (
    Base,
    CLASS_REGISTRY,
)


@celery.task(base=QueueOnce)
def sync(account_id):
    account = StripeAccount.query.get(account_id)
    session = account.organization.create_session()

    for cls in [m for n, m in CLASS_REGISTRY.items() if isclass(m) and issubclass(m, Base)]:
        # Make these parallel to speed up execution
        while True:
            conn = session.connection()
            statements, cursor, has_more = cls.sync(account)
            print(cls)
            print(statements)
            account.cursors[cls.__tablename__] = cursor
            flag_modified(account, 'cursors')

            for statement in statements:
                conn.execute(statement)

            session.commit()

            db.session.add(account)
            db.session.commit()

            if not has_more:
                break
