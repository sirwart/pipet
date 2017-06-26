import stripe
import requests

from pipet import session
from pipet.sources.stripe.models import Account

def backfill_coupons(account_id):
    account = session.query(Account).get(account_id)
    print(account_id)
    # Coupon (list)
    # BalanceTransaction (list) + Source
    #   Payout (list)
    #   Transfer (list) + [TransferReversal]
    #   Customer (list)
    #       Subscription (list) + SubscriptionItem + Plan
    #       Charge (list)
    #           Dispute (list)
    #           Refund (list)
    #       Discount (list)
    #           Invoice (list)
    #               Invoiceitem (list)
    return True