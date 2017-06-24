from datetime import datetime
import requests

from pipet import session
from pipet.sources.zendesk.models import Account, Group, Organization, Ticket, User

def backfill(account_id, start_time=0):
    account = session.query(Account).get(account_id)
    # 1. backfill tickets, users, and groups
    user_results = []
    group_results = []
    ticket_results = []
    comment_results = []
    while True:
        start = datetime.now().timestamp()
        resp = requests.get(account.api_base_url +
            '/incremental/tickets.json?include=users,groups,organizations&start_time={start_time}'.format(
                start_time=start_time), auth=(account.auth))
        if resp.status_code != 200:
            break
        print('request completed in %d seconds' % (datetime.now().timestamp() - start))
        print('processing %d tickets' % resp.json()['count'])

        data = resp.json()
        if data['count'] == 0 or start_time == data['end_time']:
            break

        start_time = data['end_time']

        for user_json in data['users']:
            if session.query(User).get(user_json['id']):
                continue
            elif user_json['id'] in [u.id for u in user_results]:
                continue

            user, _ = User.create_or_update(user_json)
            user_results.append(user)

        for group_json in data['groups']:
            if session.query(Group).get(group_json['id']):
                continue
            elif group_json['id'] in [g.id for g in group_results]:
                continue

            group, _ = Group.create_or_update(group_json)
            group_results.append(group)

        for org_json in data['organizations']:
            # TODO
            pass

        for ticket_json in data['tickets']:
            if ticket_json['status'] == 'deleted':
                continue
            elif ticket_json['id'] in [t.id for t in ticket_results]:
                continue
            elif session.query(Ticket).get(ticket_json['id']):
                continue

            ticket, _ = Ticket.create_or_update(ticket_json)
            ticket_results.append(ticket)

    session.add_all(user_results)
    session.add_all(group_results)
    session.add_all(ticket_results)
    session.commit()
    # 2. Backfill comments
    # 3. Set up targets and triggers