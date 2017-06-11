import os

import stripe

from app.stripe.models import *

STRIPE_API_KEY_URL = "https://dashboard.stripe.com/account/apikeys"
STRIPE_WEBHOOOK_URL = "https://dashboard.stripe.com/account/webhooks"

stripe = Blueprint('stripe', __name__, template_folder='templates')

@stripe.route('/')
def index():
	return 'Stripe Pipet'


@stripe.route('/activate')
def activate():
	return


@stripe.route('/deactivate')
	return


@stripe.route('/hook')
	return
