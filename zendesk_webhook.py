import os

import requests

from pipet.sources.zendesk.models import Account
from pipet import session


account = session.query(Account).get(1)
requests.post('https://' + os.environ.get('PIPET_DOMAIN') + '/zendesk/hook',
    auth=(account.subdomain, account.api_key), json={'id': 4166})
