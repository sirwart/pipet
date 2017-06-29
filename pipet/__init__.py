import json
import os

from flask import Flask, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
import raven
from raven.contrib.flask import Sentry
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateSchema, DropSchema


app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY')
engine = create_engine(os.environ.get('POSTGRES_URI'))
session = sessionmaker(bind=engine)()
sentry = Sentry(app)

import pipet.views

schemas = []
tables = []


from pipet.sources.zendesk import zendesk_blueprint
from pipet.sources.zendesk import models as zendesk_models

app.register_blueprint(zendesk_blueprint, url_prefix='/zendesk')
schemas.append(zendesk_models.SCHEMANAME)
for name in zendesk_models.ZENDESK_MODELS:
    if name == '_sa_module_registry':
        continue
    tables.append(zendesk_models.ZENDESK_MODELS.get(name))


from pipet.sources.stripe import stripe_blueprint
from pipet.sources.stripe import models as stripe_models

app.register_blueprint(stripe_blueprint, url_prefix='/stripe')
schemas.append(stripe_models.SCHEMANAME)
for name in stripe_models.STRIPE_MODELS:
    if name == '_sa_module_registry':
        continue
    tables.append(stripe_models.STRIPE_MODELS.get(name))

# Setup Scripts
def create_all():
    # Pipet Models
    from pipet.models import TABLES
    for name in TABLES:
        if name == '_sa_module_registry':
            continue
        TABLES[name].metadata.create_all(engine)

    try:
        for schema in app.blueprints:
            session.execute(CreateSchema(schema))
        session.commit()
    except sqlalchemy.exc.ProgrammingError as e:
        print(e)
        pass

    for table in tables:
        try:
            table.metadata.create_all(engine)
        except sqlalchemy.exc.ProgrammingError as e:
            print(e)
            pass


def drop_all():
    for table in tables:
        table.metadata.drop_all(engine)

    for schema in app.blueprints:
        session.execute(DropSchema(schema))
    session.commit()

    drop_all()
