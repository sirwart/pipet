import requests

from pipet.models import db
from pipet.sources.stripe.models import (
    Base,
    SCHEMANAME,
    STRIPE_API_VERSION,
)


class StripeAccount(db.Model):
    api_key = db.Column(db.Text)
    initialized = db.Column(db.Boolean)

    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'))

    organization = db.relationship('Organization', backref=db.backref(
        'stripe_account', lazy=True, uselist=False))
