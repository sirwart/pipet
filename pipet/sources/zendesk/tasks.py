from pipet.sources.zendesk.models import Account, Ticket

def backfill(account_id):
    # 1. backfill tickets, users, and groups
    # 2. Backfill comments
    # 3. Set up targets and triggers
    return True