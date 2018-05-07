from flask import Blueprint, redirect, request, Response, render_template, url_for
from flask_login import current_user, login_required
import stripe

from pipet import db
from pipet.sources.stripe import StripeAccount
from pipet.sources.stripe.forms import CreateAccountForm
from pipet.sources.stripe.models import SCHEMANAME


blueprint = Blueprint(SCHEMANAME, __name__, template_folder='templates')


@blueprint.route('/')
@login_required
def index():
    return render_template('stripe/index.html')


@blueprint.route('/activate', methods=['GET', 'POST'])
@login_required
def activate():
    session = current_user.organization.create_session()
    form = CreateAccountForm()
    account = current_user.organization.stripe_account
    if form.validate_on_submit():
        if not account:
            account = StripeAccount()

        account.api_key = form.api_key.data
        account.organization_id = current_user.organization.id

        db.session.add(account)
        db.session.commit()

        return redirect(url_for('stripe.index'))

    if account:
        form.api_key.data = account.api_key

    return render_template('stripe/activate.html', form=form)


@blueprint.route('/deactivate')
@login_required
def deactivate():
    return


@blueprint.route('/reset')
@login_required
def reset():
    session = current_user.organization.create_session()
    current_user.organization.stripe_account.drop_all(session)
    current_user.organization.stripe_account.create_all(session)
    return redirect(url_for('stripe.index'))
