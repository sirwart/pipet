from datetime import datetime

from flask_sqlalchemy import camel_to_snake_case
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import relationship
from sqlalchemy.schema import MetaData, ForeignKey
from sqlalchemy.types import Boolean, Float, Text, Integer, DateTime
import stripe

SCHEMANAME = 'stripe'
STRIPE_API_KEY_URL = 'https://dashboard.stripe.com/account/apikeys'
STRIPE_API_VERSION = '2018-02-28'
STRIPE_WEBHOOOK_URL = 'https://dashboard.stripe.com/account/webhooks'
STRIPE_MODELS = {}


@as_declarative(metadata=MetaData(schema=SCHEMANAME), class_registry=STRIPE_MODELS)
class Base(object):
    @declared_attr
    def __tablename__(cls):
        return camel_to_snake_case(cls.__name__)

    id = Column(Text, primary_key=True)

    def load_json(self, data):
        for field, value in data.items():
            if value and field in self.__table__._columns.keys():
                if isinstance(self.__table__._columns.get(field).type, DateTime):
                    setattr(self, field, datetime.fromtimestamp(value))
                # Stripe returns full objects. I only want to store the ids.
                elif isinstance(self.__table__._columns.get(field).type, ARRAY):
                    setattr(self, field, sorted([x['id'] for x in value]))
                elif isinstance(value, dict) and \
                        isinstance(self.__table__._columns.get(field).type, Text) and \
                        self.__table__._columns.get(field).foreign_keys:
                    setattr(self, field, str(value['id']))
                elif isinstance(self.__table__._columns.get(field).type, Text) and \
                        field == 'id':
                    setattr(self, field, str(value))
                else:
                    setattr(self, field, value)
            elif field == 'metadata':
                setattr(self, 'stripe_metadata', value)


class Source(Base):
    amount = Column(Integer)
    client_secret = Column(Text)
    created = Column(DateTime)
    currency = Column(Text)
    flow = Column(Text)
    stripe_metadata = Column(JSONB)
    owner = Column(JSONB)
    receiver = Column(JSONB)
    redirect = Column(JSONB)
    status = Column(Text)
    type = Column(Text)
    usage = Column(Text)


class BalanceTransaction(Base):
    amount = Column(Integer)
    available_on = Column(DateTime)
    created = Column(DateTime)
    currency = Column(Text)
    description = Column(Text)
    fee = Column(Integer)
    fee_details = Column(JSONB)
    net = Column(Integer)
    source = Column(Text, ForeignKey('source.id'))
    status = Column(Text)
    type = Column(Text)


class Charge(Base):
    amount = Column(Integer)
    amount_refunded = Column(Integer)
    application = Column(Text)
    application_fee = Column(Text)
    balance_transaction = Column(Text, ForeignKey('balance_transaction.id'))
    captured = Column(Boolean)
    created = Column(DateTime)
    currency = Column(Text)
    customer = Column(Text, ForeignKey('customer.id'))
    description = Column(Text)
    failure_code = Column(Text)
    failure_message = Column(Text)
    fraud_details = Column(JSONB)
    invoice = Column(Text, ForeignKey('invoice.id'))
    stripe_metadata = Column(JSONB, name='metadata')
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
    source_transfer = Column(Text, ForeignKey('transfer.id'), nullable=True)
    statement_descriptor = Column(Text)
    status = Column(Text)
    transfer = Column(Text, ForeignKey('transfer.id'))
    transfer_group = Column(Text)


class Customer(Base):
    account_balance = Column(Integer)
    business_vat_id = Column(Text)
    created = Column(DateTime)
    currency = Column(Text)
    default_source = Column(Text)
    delinquent = Column(Boolean)
    description = Column(Text)
    email = Column(Text)
    stripe_metadata = Column(JSONB)
    shipping = Column(JSONB)


class Dispute(Base):
    amount = Column(Integer)
    balance_transaction = Column(Text)
    balance_transactions = Column(ARRAY(Text, dimensions=1))
    charge = Column(Text, ForeignKey('charge.id'))
    created = Column(DateTime)
    currency = Column(Text)
    evidence = Column(JSONB)
    evidence_details = Column(JSONB)
    is_charge_refundable = Column(Boolean)
    stripe_metadata = Column(JSONB, name='metadata')
    reason = Column(Text)
    status = Column(Text)


class Payout(Base):
    amount = Column(Integer)
    arrival_date = Column(DateTime)
    balance_transaction = Column(Text, ForeignKey('balance_transaction.id'))
    created = Column(DateTime)
    currency = Column(Text)
    description = Column(Text)
    destination = Column(Text)
    failure_balance_transaction = Column(
        Text, ForeignKey('balance_transaction.id'))
    failure_code = Column(Text)
    failure_message = Column(Text)
    stripe_metadata = Column(JSONB, name='metadata')
    method = Column(Text)
    source_type = Column(Text)
    statement_descriptor = Column(Text)
    status = Column(Text)
    type = Column(Text)


class Refund(Base):
    amount = Column(Integer)
    balance_transaction = Column(Text, ForeignKey('balance_transaction.id'))
    charge = Column(Text, ForeignKey('charge.id'))
    created = Column(DateTime)
    currency = Column(Text)
    description = Column(Text)
    reason = Column(Text)
    receipt_number = Column(Text)
    status = Column(Text)


class Coupon(Base):
    amount_off = Column(Integer)
    created = Column(DateTime)
    currency = Column(Text)
    duration = Column(Text)
    duration_in_months = Column(Integer)
    max_redemptions = Column(Integer)
    stripe_metadata = Column(JSONB)
    percent_off = Column(Integer)
    redeem_by = Column(DateTime)
    times_redeemed = Column(Integer)
    valid = Column(Boolean)

    @staticmethod
    def backfill(account_id):
        print(account_id)


class Discount(Base):
    coupon = Column(Text, ForeignKey('coupon.id'))
    customer = Column(Text, ForeignKey('customer.id'))
    end = Column(DateTime)
    start = Column(DateTime)
    subscription = Column(Text, ForeignKey('subscription.id'))


class Invoice(Base):
    amount_due = Column(Integer)
    application_fee = Column(Integer)
    attempt_count = Column(Integer)
    attempted = Column(Boolean)
    charge = Column(Text, ForeignKey('charge.id'))
    closed = Column(Boolean)
    currency = Column(Text)
    customer = Column(Text, ForeignKey('customer.id'))
    date = Column(DateTime)
    description = Column(Text)
    discount = Column(Text, ForeignKey('discount.id'))
    ending_balance = Column(Integer)
    forgiven = Column(Boolean)
    stripe_metadata = Column(JSONB, name='metadata')
    next_payment_attempt = Column(DateTime)
    paid = Column(Boolean)
    period_end = Column(DateTime)
    period_start = Column(DateTime)
    receipt_number = Column(Text)
    starting_balance = Column(Integer)
    statement_descriptor = Column(Text)
    subscription = Column(Text, ForeignKey('subscription.id'))
    subscription_proration_date = Column(Integer)
    subtotal = Column(Integer)
    tax = Column(Integer)
    tax_percent = Column(Float)
    total = Column(Integer)
    webhooks_delivered_at = Column(DateTime)


class InvoiceItem(Base):
    amount = Column(Integer)
    currency = Column(Text)
    customer = Column(Text, ForeignKey('customer.id'))
    date = Column(DateTime)
    description = Column(Text)
    discountable = Column(Boolean)
    invoice = Column(Text, ForeignKey('invoice.id'))
    stripe_metadata = Column(JSONB, name='metadata')
    period = Column(JSONB)
    plan = Column(Text, ForeignKey('plan.id'))
    proration = Column(Boolean)
    quantity = Column(Integer)
    subscription = Column(Text, ForeignKey('subscription.id'))
    subscription_item = Column(Text, ForeignKey('subscription_item.id'))


class Plan(Base):
    amount = Column(Integer)
    created = Column(DateTime)
    currency = Column(Text)
    interval = Column(Text)
    interval_count = Column(Integer)
    stripe_metadata = Column(JSONB, name='metadata')
    name = Column(Text)
    statement_descriptor = Column(Text)
    trial_period_days = Column(Integer)


class Subscription(Base):
    application_fee_percent = Column(Float)
    cancel_at_period_end = Column(Boolean)
    canceled_at = Column(DateTime)
    created = Column(DateTime)
    current_period_end = Column(DateTime)
    current_period_start = Column(DateTime)
    customer = Column(Text, ForeignKey('customer.id'))
    discount = Column(Text, ForeignKey('discount.id'))
    ended_at = Column(DateTime)
    stripe_metadata = Column(JSONB, name='metadata')
    plan = Column(Text, ForeignKey('plan.id'))
    quantity = Column(Integer)
    start = Column(DateTime)
    status = Column(Text)
    tax_percent = Column(Float)
    trial_end = Column(DateTime)
    trial_start = Column(DateTime)


class SubscriptionItem(Base):
    created = Column(DateTime)
    plan = Column(Text, ForeignKey('plan.id'))
    quantity = Column(Integer)


class Transfer(Base):
    amount = Column(Integer)
    amount_reversed = Column(Integer)
    balance_transaction = Column(Text, ForeignKey('balance_transaction.id'))
    created = Column(DateTime)
    currency = Column(Text)
    description = Column(Text)
    destination = Column(Text)
    destination_payment = Column(Text)
    stripe_metadata = Column(JSONB, name='metadata')
    reversed = Column(Boolean)
    source_transaction = Column(Text)
    source_type = Column(Text)
    transfer_group = Column(Text)


class TransferReversal(Base):
    amount = Column(Integer)
    balance_transaction = Column(Text, ForeignKey('balance_transaction.id'))
    created = Column(DateTime)
    currency = Column(Text)
    stripe_metadata = Column(JSONB)
    transfer = Column(Text, ForeignKey('transfer.id'))
