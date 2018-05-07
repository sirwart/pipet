from contextlib import contextmanager
from datetime import datetime
from inspect import isclass

from celery import chord
from celery_once import QueueOnce
from celery.schedules import crontab
from celery.utils.log import get_task_logger
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.sql import func

from pipet import celery, db
from pipet.models import Organization
from pipet.sources.zendesk import ZendeskAccount
from pipet.sources.zendesk.models import (
    Base,
    CLASS_REGISTRY,
)


logger = get_task_logger(__name__)


@celery.task(base=QueueOnce)
def sync(account_id):
    account = ZendeskAccount.query.get(account_id)
    session = account.organization.create_session()

    for cls in [m for n, m in CLASS_REGISTRY.items() if isclass(m) and issubclass(m, Base)]:
        # Make these parallel to speed up execution
        while True:
            conn = session.connection()
            statments, cursor, has_more = cls.sync(account)
            account.cursors[cls.__tablename__] = cursor
            flag_modified(account, 'cursors')

            for statement in statments:
                conn.execute(statement)

            session.commit()

            db.session.add(account)
            db.session.commit()

            if not has_more:
                break
