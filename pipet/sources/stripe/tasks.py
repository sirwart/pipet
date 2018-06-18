from celery_once import QueueOnce

from pipet import celery, db
from pipet.sources.stripe import StripeAccount


@celery.task(base=QueueOnce)
def sync(account_id):
    account = StripeAccount.query.get(account_id)
    if account.backfilled:
        account.update()
    else:
        account.backfill()
