from datetime import datetime

from flask_sqlalchemy import camel_to_snake_case
from requests.exceptions import HTTPError
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import relationship
from sqlalchemy.schema import MetaData, ForeignKey
from sqlalchemy.types import Boolean, Float, Text, BigInteger, DateTime
import stripe

from pipet.utils import PipetBase


STRIPE_API_KEY_URL = 'https://dashboard.stripe.com/account/apikeys'
STRIPE_API_VERSION = '2018-02-28'
SCHEMANAME = 'stripe'
CLASS_REGISTRY = {}


@as_declarative(metadata=MetaData(schema=SCHEMANAME), class_registry=CLASS_REGISTRY)
class Base(PipetBase):
    id = Column(Text, primary_key=True)

    @classmethod
    def parse(cls, data):
        d = {}
        for field, column in cls.__table__._columns.items():
            # metadata is not a valid column name
            value = data.get('meta' if field == 'metadata' else field, None)
            if not value:
                continue
            elif isinstance(column.type, DateTime):
                # We assume GMT
                d[field] = datetime.fromtimestamp(value)
            else:
                d[field] = value
        return d

    @classmethod
    def sync(cls, account):
        statements = []
        cursor = account.cursors.get(cls.__tablename__)
        resp = account.get(cls.endpoint, params={'starting_after': cursor})

        try:
            resp.raise_for_status()
        except HTTPError:
            if resp.status_code == 429:
                return statements, cursor, False
            raise HTTPError

        ns, cursor = cls.process_response(resp, cursor)
        statements += ns

        return statements, cursor, resp.json()['has_more']

    @classmethod
    def process_response(cls, response, cursor=None):
        statements = []
        for data in response.json()['data']:
            cursor = data['id']
            statements.append(cls.upsert(cls.parse(data)))
        return statements, cursor


class Source(Base):
    amount = Column(BigInteger)
    client_secret = Column(Text)
    created = Column(DateTime)
    currency = Column(Text)
    flow = Column(Text)
    meta = Column(JSONB, name='metadata')
    owner = Column(JSONB)
    receiver = Column(JSONB)
    redirect = Column(JSONB)
    status = Column(Text)
    type = Column(Text)
    usage = Column(Text)

    @classmethod
    def sync(cls, account):
        return [], None, False


class BalanceTransaction(Base):
    amount = Column(BigInteger)
    available_on = Column(DateTime)
    created = Column(DateTime)
    currency = Column(Text)
    description = Column(Text)
    exchange_rate = Column(Float)
    fee = Column(BigInteger)
    fee_details = Column(JSONB)
    net = Column(BigInteger)
    source = Column(Text)
    status = Column(Text)
    type = Column(Text)

    endpoint = '/v1/balance/history'


class Charge(Base):
    amount = Column(BigInteger)
    amount_refunded = Column(BigInteger)
    application = Column(Text)
    application_fee = Column(Text)
    balance_transaction = Column(Text)
    captured = Column(Boolean)
    created = Column(DateTime)
    currency = Column(Text)
    customer = Column(Text)
    description = Column(Text)
    failure_code = Column(Text)
    failure_message = Column(Text)
    fraud_details = Column(JSONB)
    invoice = Column(Text)
    meta = Column(JSONB, name='metadata')
    on_behalf_of = Column(Text)
    order = Column(Text)
    outcome = Column(JSONB)
    paid = Column(Boolean)
    receipt_email = Column(Text)
    receipt_number = Column(Text)
    refunded = Column(Boolean)
    refunds = Column(JSONB)
    review = Column(Text)
    shipping = Column(JSONB)
    source = Column(JSONB)
    source_transfer = Column(Text, nullable=True)
    statement_descriptor = Column(Text)
    status = Column(Text)
    transfer = Column(Text)
    transfer_group = Column(Text)

    endpoint = '/v1/charges'


class Customer(Base):
    account_balance = Column(BigInteger)
    business_vat_id = Column(Text)
    created = Column(DateTime)
    currency = Column(Text)
    default_source = Column(Text)
    delinquent = Column(Boolean)
    description = Column(Text)
    email = Column(Text)
    meta = Column(JSONB, name='metadata')
    shipping = Column(JSONB)

    endpoint = '/v1/customers'


class Dispute(Base):
    amount = Column(BigInteger)
    balance_transaction = Column(Text)
    balance_transactions = Column(ARRAY(Text, dimensions=1))
    charge = Column(Text)
    created = Column(DateTime)
    currency = Column(Text)
    evidence = Column(JSONB)
    evidence_details = Column(JSONB)
    is_charge_refundable = Column(Boolean)
    meta = Column(JSONB, name='metadata')
    reason = Column(Text)
    status = Column(Text)

    endpoint = '/v1/disputes'


class Payout(Base):
    amount = Column(BigInteger)
    arrival_date = Column(DateTime)
    balance_transaction = Column(Text)
    created = Column(DateTime)
    currency = Column(Text)
    description = Column(Text)
    destination = Column(Text)
    failure_balance_transaction = Column(
        Text)
    failure_code = Column(Text)
    failure_message = Column(Text)
    meta = Column(JSONB, name='metadata')
    method = Column(Text)
    source_type = Column(Text)
    statement_descriptor = Column(Text)
    status = Column(Text)
    type = Column(Text)

    endpoint = '/v1/payouts'


class Refund(Base):
    amount = Column(BigInteger)
    balance_transaction = Column(Text)
    charge = Column(Text)
    created = Column(DateTime)
    currency = Column(Text)
    description = Column(Text)
    reason = Column(Text)
    receipt_number = Column(Text)
    status = Column(Text)

    endpoint = '/v1/refunds'


class Coupon(Base):
    amount_off = Column(BigInteger)
    created = Column(DateTime)
    currency = Column(Text)
    duration = Column(Text)
    duration_in_months = Column(BigInteger)
    max_redemptions = Column(BigInteger)
    meta = Column(JSONB, name='metadata')
    percent_off = Column(BigInteger)
    redeem_by = Column(DateTime)
    times_redeemed = Column(BigInteger)
    valid = Column(Boolean)

    endpoint = '/v1/coupons'


class Discount(Base):
    coupon = Column(Text)
    customer = Column(Text)
    end = Column(DateTime)
    start = Column(DateTime)

    @classmethod
    def sync(cls, account):
        return [], None, False


class Invoice(Base):
    amount_due = Column(BigInteger)
    application_fee = Column(BigInteger)
    attempt_count = Column(BigInteger)
    attempted = Column(Boolean)
    charge = Column(Text)
    closed = Column(Boolean)
    currency = Column(Text)
    customer = Column(Text)
    date = Column(DateTime)
    description = Column(Text)
    discount = Column(Text)
    ending_balance = Column(BigInteger)
    forgiven = Column(Boolean)
    meta = Column(JSONB, name='metadata')
    next_payment_attempt = Column(DateTime)
    paid = Column(Boolean)
    period_end = Column(DateTime)
    period_start = Column(DateTime)
    receipt_number = Column(Text)
    starting_balance = Column(BigInteger)
    statement_descriptor = Column(Text)
    subscription = Column(Text)
    subscription_proration_date = Column(BigInteger)
    subtotal = Column(BigInteger)
    tax = Column(BigInteger)
    tax_percent = Column(Float)
    total = Column(BigInteger)
    webhooks_delivered_at = Column(DateTime)

    endpoint = '/v1/invoices'


class InvoiceItem(Base):
    amount = Column(BigInteger)
    currency = Column(Text)
    customer = Column(Text)
    date = Column(DateTime)
    description = Column(Text)
    discountable = Column(Boolean)
    invoice = Column(Text)
    meta = Column(JSONB, name='metadata')
    period = Column(JSONB)
    plan = Column(Text)
    proration = Column(Boolean)
    quantity = Column(BigInteger)
    subscription = Column(Text)
    subscription_item = Column(Text)

    endpoint = '/v1/invoiceitems'


class Plan(Base):
    amount = Column(BigInteger)
    created = Column(DateTime)
    currency = Column(Text)
    interval = Column(Text)
    interval_count = Column(BigInteger)
    meta = Column(JSONB, name='metadata')
    name = Column(Text)
    statement_descriptor = Column(Text)
    trial_period_days = Column(BigInteger)

    endpoint = '/v1/plans'


class Subscription(Base):
    application_fee_percent = Column(Float)
    cancel_at_period_end = Column(Boolean)
    canceled_at = Column(DateTime)
    created = Column(DateTime)
    current_period_end = Column(DateTime)
    current_period_start = Column(DateTime)
    customer = Column(Text)
    discount = Column(Text)
    ended_at = Column(DateTime)
    meta = Column(JSONB, name='metadata')
    plan = Column(Text)
    quantity = Column(BigInteger)
    start = Column(DateTime)
    status = Column(Text)
    tax_percent = Column(Float)
    trial_end = Column(DateTime)
    trial_start = Column(DateTime)

    endpoint = '/v1/subscriptions'

    @classmethod
    def sync(cls, account):
        statements = []
        cursor = account.cursors.get(cls.__tablename__)
        resp = account.get(cls.endpoint, params={'starting_after': cursor})

        try:
            resp.raise_for_status()
        except HTTPError:
            if resp.status_code == 429:
                return statements, cursor, False
            raise HTTPError

        ns, cursor = cls.process_response(resp, cursor)
        statements += ns

        return statements, cursor, resp.json()['has_more']

    @classmethod
    def process_response(cls, response, cursor=None):
        statements = []
        for data in response.json()['data']:
            cursor = data['id']
            statements.append(cls.upsert(cls.parse(data)))

            resp = account.get(SubscriptionItem.endpoint,
                               params={'subscription': cursor})

            si_cursor = None
            while True:
                si_statements, si_cursor, has_more = SubscriptionItem.sync_for_subscription(
                    account, cursor, si_cursor)
                statements += si_statements

                if not has_more:
                    break

        return statements, cursor


class SubscriptionItem(Base):
    created = Column(DateTime)
    plan = Column(Text)
    quantity = Column(BigInteger)

    endpoint = '/v1/subscription_items'

    @classmethod
    def sync(cls, account):
        return [], None, False

    @classmethod
    def sync_for_subscription(cls, account, subscription_id, cursor):
        statements = []
        resp = account.get(cls.endpoint, params={
                           'starting_after': cursor, 'subscription': subscription_id})

        try:
            resp.raise_for_status()
        except HTTPError:
            if resp.status_code == 429:
                return statements, cursor, False
            raise HTTPError

        ns, cursor = cls.process_response(resp, cursor)
        statements += ns

        return statements, cursor, resp.json()['has_more']


class Transfer(Base):
    amount = Column(BigInteger)
    amount_reversed = Column(BigInteger)
    balance_transaction = Column(Text)
    created = Column(DateTime)
    currency = Column(Text)
    description = Column(Text)
    destination = Column(Text)
    destination_payment = Column(Text)
    meta = Column(JSONB, name='metadata')
    reversed = Column(Boolean)
    source_transaction = Column(Text)
    source_type = Column(Text)
    transfer_group = Column(Text)

    endpoint = '/v1/transfers'


class TransferReversal(Base):
    amount = Column(BigInteger)
    balance_transaction = Column(Text)
    created = Column(DateTime)
    currency = Column(Text)
    meta = Column(JSONB, name='metadata')
    transfer = Column(Text)

    @classmethod
    def sync(cls, account):
        return [], None, False
