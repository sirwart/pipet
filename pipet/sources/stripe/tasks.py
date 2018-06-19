from datetime import datetime
import time

from celery import group
from celery_once import QueueOnce

from pipet import app, celery, db
from pipet.sources.stripe import StripeAccount


@celery.task(base=QueueOnce, once={'graceful': True})
def sync(account_id):
    with app.app_context():
        account = StripeAccount.query.get(account_id)
        if account.backfilled:
            account.update()
        else:
            account.backfill()


@celery.task
def sync_all():
    job = group([sync.s(account.id) for account in StripeAccount.query.all()])
    job.apply_async()
