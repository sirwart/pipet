from pipet.souces.stripe.models import Account

def backfill():
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