import stripe
import requests

from pipet import session
from pipet.sources.stripe.models import (
    Account,
    Source,
    BalanceTransaction,
    Charge,
    Coupon,
    Customer,
    Dispute,
    Payout,
    Plan,
    Refund,
    Coupon,
    Discount,
    Invoice,
    InvoiceItem,
    Plan,
    Subscription,
    SubscriptionItem,
    Transfer,
)

def backfill_coupons(account_id):
    account = session.query(Account).get(account_id)

    coupons = account.client.Coupon.list(limit=100)
    for coupon in coupons.auto_paging_iter():
        pass

    sources = stripe.Source.list(limit=100)
    for source in sources.auto_paging_iter():
        pass

    charges = stripe.Charge.list(limit=100)
    for charge in charges.auto_paging_iter():
        pass

    stripe_classes = [Source, BalanceTransaction, Payout, Transfer, TransferReversal, Customer, Coupon, Plan,
        Subscription, SubscriptionItem, Discount, Invoice, Charge, Refund, Dispute, InvoiceItem]

    for stripe_class in stripe_classes:
        objs = getattr(stripe, stripe_class).list(limit=100)
        for result_obj in objs.auto_paging_iter():
            inst = stripe_class()
            inst.load_json(result_obj.json())
            session.add(inst)
        session.commit()
