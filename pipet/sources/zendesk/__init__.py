from datetime import datetime
from functools import wraps
import os
from threading import Thread

from flask import Blueprint, redirect, request, Response, render_template, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
import requests
from wtforms import StringField, validators
from wtforms.fields.html5 import EmailField

from pipet import engine, session
from pipet.sources.zendesk.models import (
    SCHEMANAME,
    ZENDESK_MODELS,
    Account,
    Ticket,
)
from pipet.sources.zendesk.tasks import backfill_tickets


zendesk_blueprint = Blueprint(SCHEMANAME, __name__, template_folder='templates')


class AccountForm(FlaskForm):
    subdomain = StringField('Subdomain', validators=[validators.DataRequired()])
    admin_email = EmailField('Admin Email', validators=[validators.DataRequired()])
    api_key = StringField('API Key', validators=[validators.DataRequired()])


@zendesk_blueprint.route('/')
@login_required
def index():
    return render_template('zendesk/index.html')


@zendesk_blueprint.route('/activate', methods=['GET', 'POST'])
@login_required
def activate():
    form = AccountForm()
    account = session.query(Account).filter(Account.workspace == current_user).first()
    if form.validate_on_submit():
        if not account:
            account = Account(
                subdomain=form.subdomain.data,
                admin_email=form.admin_email.data,
                api_key=form.api_key.data,
                workspace_id=current_user.id)
        if not account.target_exists:
            account.create_target()
        if not account.trigger_exists:
            account.create_trigger()
        session.add(account)
        session.commit()
        return redirect(url_for('zendesk.index'))
    
    if account:
        form.subdomain.data = account.subdomain
        form.admin_email.data = account.admin_email
        form.api_key.data = account.api_key

    return render_template('zendesk/activate.html', form=form)


@zendesk_blueprint.route('/backfill')
@login_required
def backfill():
    account = session.query(Account).filter(Account.workspace == current_user).first()
    t = Thread(target=backfill_tickets, args=(account.id, ))
    t.setDaemon(True)
    t.start()
    return redirect(url_for('zendesk.index'))


@zendesk_blueprint.route('/deactivate')
def deactivate():
    account = session.query(Account).filter(Account.workspace == current_user).first()
    account.destroy_target()
    account.destroy_trigger()
    session.add(account)
    session.commit()
    return redirect(url_for('zendesk.index'))


@zendesk_blueprint.route("/hook", methods=['POST'])
def hook():
    if not request.authorization:
        return ('', 401)

    account = session.query(Account).filter((Account.subdomain == request.authorization.username) &
        (Account.api_key == request.authorization.password)).first()

    if not account:
        return ('', 401)

    ticket_id = request.get_json()['id']
    resp = requests.get(account.api_base_url + \
        '/tickets/{id}.json?include=users,groups'.format(id=ticket_id),
        auth=account.auth)

    ticket, _ = Ticket.create_or_update(resp.json()['ticket'])
    session.add_all(ticket.update(resp.json()))
    session.add(ticket)

    # resp = requests.get(account.api_base_url + \
    #     '/tickets/{id}/comments.json'.format(id=ticket.id), auth=account.auth)

    # session.add_all(ticket.update_comments(resp.json()['comments']))
    session.commit()
    return ('', 204)
