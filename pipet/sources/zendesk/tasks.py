from datetime import datetime
import requests

from sqlalchemy.sql import func

from pipet import session
from pipet.sources.zendesk.models import Account, Group, Organization, Ticket, TicketComment, User


def backfill_tickets(account_id, start_time=0):
    backfill_start_time = datetime.now()
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

            user, _ = User.create_or_update(user_json, account)
            user_results.append(user)

        for group_json in data['groups']:
            if session.query(Group).get(group_json['id']):
                continue
            elif group_json['id'] in [g.id for g in group_results]:
                continue

            group, _ = Group.create_or_update(group_json, account)
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

            ticket, _ = Ticket.create_or_update(ticket_json, account)
            ticket_results.append(ticket)

    session.add_all(user_results)
    session.add_all(group_results)
    session.add_all(ticket_results)
    session.commit()

    comments = []
    tickets = session.query(Ticket).all()
    ticket_comment_processed = 0
    print('adding comments for %d tickets' % len(tickets))
    for ticket in tickets:
        ticket_comment_processed += 1
        print('adding comments for %d / %d tickets' % (ticket_comment_processed, len(tickets)))

        query = session.query(func.max(TicketComment.created_at))
        max_comments_time = query.filter(TicketComment.ticket_id == ticket.id).group_by(TicketComment.ticket_id).first()
        if max_comments_time and ticket.updated_at == max_comments_time[0]:
            continue

        resp = requests.get(account.api_base_url + \
            '/tickets/{id}/comments.json'.format(id=ticket.id),
            auth=account.auth)
        assert resp.status_code == 200
        comments = ticket.update_comments(resp.json()['comments'])
        session.add_all(comments)
        session.commit()

    print('backfill complete, took %d seconds' % int((datetime.now() - backfill_start_time).total_seconds()))
