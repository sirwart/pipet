import os

from flask import Blueprint, redirect, request, Response, render_template, url_for
# import stripe
import sqlalchemy

from .models import (
    SCHEMANAME,
    STRIPE_API_VERSION,
    STRIPE_MODELS,
    Account,
    Source,
    BalanceTransaction,
    Charge,
    Customer,
    Dispute,
    Payout,
    Refund,
    Coupon,
    Discount,
    Invoice,
    Invoiceitem,
    Plan,
    Subscription,
    SubscriptionItem,
    Transfer
)
from pipet import engine, q, session

STRIPE_API_KEY_URL = "https://dashboard.stripe.com/account/apikeys"
STRIPE_WEBHOOOK_URL = "https://dashboard.stripe.com/account/webhooks"

stripe_blueprint = Blueprint(SCHEMANAME, __name__, template_folder='templates')


from pipet.sources.zendesk.tasks import backfill
@stripe_blueprint.route('/test')
def test():
    job = q.enqueue(backfill)
    return job.id


@stripe_blueprint.route('/')
def index():
    return 'Stripe Pipet'


@stripe_blueprint.route('/activate')
def activate():
    """Instructions on getting webhooks set up"""
    return


@stripe_blueprint.route('/deactivate')
def deactivate():
    return


@stripe_blueprint.route('/hook', methods=['POST'])
def hook():
    data = request.get_json()
    assert data['api_version'] == STRIPE_API_VERSION

    tablenames = {m.__tablename__: m for c, m in STRIPE_MODELS.items() \
        if isinstance(m, sqlalchemy.ext.declarative.api.DeclarativeMeta)}
    obj_json = data['data']['object']
    obj_type = obj_json['object']
    
    if obj_type in tablenames:
        model = tablenames[obj_type]
        event_type = data['type'].split('.')
        i = session.query(model).get(obj_json['id'])

        if event_type[-1] == 'deleted':
            i.delete()
        elif event_type[-1] == 'created':
            # create object
            i = model()

        i.load_json(obj_json)
        session.add(i)

    session.commit()
    return '', 201

