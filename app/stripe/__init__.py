import os

from flask import Blueprint, redirect, request, Response, render_template, url_for
import stripe

from app.stripe.models import BalanceTransaction, SCHEMANAME

STRIPE_API_KEY_URL = "https://dashboard.stripe.com/account/apikeys"
STRIPE_WEBHOOOK_URL = "https://dashboard.stripe.com/account/webhooks"

stripe = Blueprint(SCHEMANAME, __name__, template_folder='templates')

@stripe.route('/')
def index():
    return 'Stripe Pipet'


@stripe.route('/activate')
def activate():
    return


@stripe.route('/deactivate')
def deactivate():
    return


@stripe.route('/hook')
def hook():
    return
