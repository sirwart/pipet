from datetime import datetime

from flask import Blueprint, redirect, request, Response, render_template, url_for
from flask_login import current_user, login_required
import requests
from sqlalchemy.exc import ProgrammingError

from pipet import db
from pipet.sources.zendesk import ZendeskAccount
from pipet.sources.zendesk.forms import CreateAccountForm, DestroyAccountForm
from pipet.sources.zendesk.models import Base, SCHEMANAME
from pipet.sources.zendesk.tasks import sync


blueprint = Blueprint(SCHEMANAME, __name__, template_folder='templates')


@blueprint.route('/')
@login_required
def index():
    return render_template('zendesk/index.html')


@blueprint.route('/activate', methods=['GET', 'POST'])
@login_required
def activate():
    session = current_user.organization.create_session()
    form = CreateAccountForm(obj=current_user.organization.zendesk_account)
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
        db.session.add(account)
        db.session.commit()
        return redirect(url_for('zendesk.index'))

    return render_template('zendesk/deactivate.html')


@blueprint.route('/reset')
@login_required
def reset():
    session = current_user.organization.create_session()
    current_user.organization.zendesk_account.drop_all(session)
    current_user.organization.zendesk_account.create_all(session)
    return redirect(url_for('zendesk.index'))


@blueprint.route("/hook", methods=['POST'])
def hook():
    if not request.authorization:
        return ('', 401)

    account = Account.query.filter((Account.subdomain == request.authorization.username) &
                                   (Account.api_key == request.authorization.password)).first()

    scoped_session = account.organization.create_scoped_session()
    session = scoped_session()

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
