from datetime import datetime
import requests

from celery.utils.log import get_task_logger
from sqlalchemy.sql import func

from pipet import celery, db
from pipet.models import Organization
from pipet.sources.zendesk import ZendeskAccount
from pipet.sources.zendesk.models import (
    Group,
    Organization,
    Ticket,
    TicketComment,
    User,
)


logger = get_task_logger(__name__)


@celery.task
def backfill(account_id, start_time=0):
    backfill_start_time = datetime.now()
    account = ZendeskAccount.query.get(account_id)
    scoped_session = account.organization.create_scoped_session()
    session = scoped_session()

    # 1. backfill tickets, users, and groups
    user_results = []
    group_results = []
    ticket_results = []
    comment_results = []

    while True:
        start = datetime.now().timestamp()
        resp = requests.get(account.base_url +
                            '/incremental/tickets.json?include=users,groups,organizations&start_time={start_time}'.format(
                                start_time=start_time), auth=(account.auth))
        if resp.status_code != 200:
            break
        logger.info('request completed in %d seconds' %
                    (datetime.now().timestamp() - start))
        logger.info('processing %d tickets' % resp.json()['count'])

        data = resp.json()
        if data['count'] == 0 or start_time == data['end_time']:
            break

        start_time = data['end_time']

        for user_json in data['users']:
            if session.query(User).get(user_json['id']):
                continue
            elif user_json['id'] in [u.id for u in user_results]:
                continue

            user, _ = User.create_or_update(session, user_json, account)
            user_results.append(user)

        for group_json in data['groups']:
            if session.query(Group).get(group_json['id']):
                continue
            elif group_json['id'] in [g.id for g in group_results]:
                continue

            group, _ = Group.create_or_update(session, group_json, account)
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

            ticket, _ = Ticket.create_or_update(session, ticket_json, account)
            ticket_results.append(ticket)

    session.add_all(user_results)
    session.add_all(group_results)
    session.add_all(ticket_results)
    session.commit()
    comments = []
    tickets = session.query(Ticket).all()
    ticket_comment_processed = 0

    logger.info('adding comments for %d tickets' % len(tickets))

    for ticket in tickets:
        ticket_comment_processed += 1
        logger.info('adding comments for %d / %d tickets' %
                    (ticket_comment_processed, len(tickets)))

        query = session.query(func.max(TicketComment.created_at))
        max_comments_time = query.filter(TicketComment.ticket_id == ticket.id).group_by(
            TicketComment.ticket_id).first()
        if max_comments_time and ticket.updated_at == max_comments_time[0]:
            continue

        resp = requests.get(account.base_url +
                            '/tickets/{id}/comments.json'.format(id=ticket.id),
                            auth=account.auth)
        assert resp.status_code == 200
        comments = ticket.update_comments(session, resp.json()['comments'])
        session.add_all(comments)
        session.commit()

    logger.info('Backfill complete, took %d seconds' %
                int((datetime.now() - backfill_start_time).total_seconds()))
