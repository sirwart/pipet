import os
import pytest
from unittest import TestCase

from dotenv import find_dotenv, load_dotenv
import stripe


load_dotenv(find_dotenv())
TEST_STRIPE_API_KEY = os.environ.get('TEST_STRIPE_API_KEY')
stripe.api_key = TEST_STRIPE_API_KEY


class StripeTest(TestCase):
    def test_customers(self):
        # Delete all existing objects
        for customer in stripe.Customer.list().auto_paging_iter():
            customer.delete()

        # create customers
        customers_created = [stripe.Customer.create() for i in range(101)]
