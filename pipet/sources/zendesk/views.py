from datetime import datetime
from functools import wraps
import os
from threading import Thread

from flask import Blueprint, redirect, request, Response, render_template, url_for
from flask_login import current_user, login_required
import requests
from sqlalchemy.exc import ProgrammingError

from pipet import db
from pipet.sources.zendesk import ZendeskAccount
from pipet.sources.zendesk.forms import CreateAccountForm, DestroyAccountForm
from pipet.sources.zendesk.models import Base
from pipet.sources.zendesk.tasks import hello

blueprint = Blueprint('zendesk', __name__, template_folder='templates')


@blueprint.route('/')
@login_required
def index():
    hello.delay()
    return render_template('zendesk/index.html')


@blueprint.route('/activate', methods=['GET', 'POST'])
@login_required
def activate():
    form = CreateAccountForm()
    account = current_user.organization.zendesk_account
    if form.validate_on_submit():
        if not account:
            account = ZendeskAccount()

        account.subdomain = form.subdomain.data
        account.admin_email = form.admin_email.data
        account.api_key = form.api_key.data
        account.organization_id = current_user.organization.id

        db.session.add(account)
        db.session.commit()

        if not account.target_exists:
            account.create_target()
        if not account.trigger_exists:
            account.create_trigger()
        if not account.initialized:
            account.create_all()

        db.session.add(account)
        db.session.commit()

        # if form.backfill.data:
        #     t = Thread(target=backfill_tickets, args=(account.id, ))
        #     t.setDaemon(True)
        #     t.start()

        return redirect(url_for('zendesk.index'))

    if account:
        form.subdomain.data = account.subdomain
        form.admin_email.data = account.admin_email
        form.api_key.data = account.api_key

    return render_template('zendesk/activate.html', form=form)


@blueprint.route('/deactivate')
@login_required
def deactivate():
    account = current_user.organization.zendesk_account
    form = DestroyAccountForm()
    if form.validate_on_submit() and form.drop.data:
        account.destroy_target()
        account.destroy_trigger()
        account.drop_all()
        session.add(account)
        session.commit()
        return redirect(url_for('zendesk.index'))

    return render_template('zendesk/deactivate.html')


@blueprint.route("/hook", methods=['POST'])
def hook():
    if not request.authorization:
        return ('', 401)

    account = Account.query.filter((Account.subdomain == request.authorization.username) &
                                   (Account.api_key == request.authorization.password)).first()

    if not account:
        return ('', 401)

    ticket_id = request.get_json()['id']
    resp = requests.get(account.api_base_url +
                        '/tickets/{id}.json?include=users,groups'.format(
                            id=ticket_id),
                        auth=account.auth)

    ticket, _ = Ticket.create_or_update(resp.json()['ticket'], account)
    session.add_all(ticket.update(resp.json()))
    session.add(ticket)

    resp = requests.get(account.api_base_url +
                        '/tickets/{id}/comments.json'.format(id=ticket.id), auth=account.auth)

    session.add_all(ticket.update_comments(resp.json()['comments']))
    session.commit()
    return ('', 204)