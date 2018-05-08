from pipet import celery
from pipet.models import Organization


@celery.task
def process_event(organization_id, data):
    pass


@celery.task
def process_page(organization_id, data):
    pass
