import json
import os

from flask import Flask, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateSchema, DropSchema

from pipet.models import Workspace

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY')

engine = create_engine(os.environ.get('SQLALCHEMY_URI'))
session = sessionmaker(bind=engine)()

from rq import Queue
from redis import Redis

redis_conn = Redis()
q = Queue(connection=redis_conn)


schemas = []
tables = []

# import app.admin as admin_blueprint
# app.register_blueprint(admin_blueprint.app)
# for name in admin_blueprint.models.TABLES:
#     tables.append(admin_blueprint.models.TABLES.get(name))


import pipet.sources.zendesk as zendesk_blueprint

app.register_blueprint(zendesk_blueprint.app, url_prefix='/zendesk')
schemas.append(zendesk_blueprint.models.SCHEMANAME)
for name in zendesk_blueprint.models.ZENDESK_MODELS:
    if name == '_sa_module_registry':
        continue
    tables.append(zendesk_blueprint.models.ZENDESK_MODELS.get(name))


import pipet.sources.stripe as stripe_blueprint

app.register_blueprint(stripe_blueprint.stripe, url_prefix='/stripe')
schemas.append(stripe_blueprint.models.SCHEMANAME)
for name in stripe_blueprint.models.STRIPE_MODELS:
    if name == '_sa_module_registry':
        continue
    tables.append(stripe_blueprint.models.STRIPE_MODELS.get(name))

import pipet.views

# Setup Scripts
def create_all():
    # PIpet Models
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
