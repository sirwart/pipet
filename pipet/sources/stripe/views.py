from flask import Blueprint, redirect, request, Response, render_template, url_for
from flask_login import current_user, login_required
import stripe

from pipet.sources.stripe.models import SCHEMANAME


blueprint = Blueprint(SCHEMANAME, __name__, template_folder='templates')


@blueprint.route('/')
@login_required
def index():
    return render_template('stripe/index.html')


@blueprint.route('/activate', methods=['GET', 'POST'])
@login_required
def activate():
    """Instructions on getting webhooks set up"""
    return


@blueprint.route('/deactivate')
@login_required
def deactivate():
    return


@blueprint.route('/reset')
@login_required
def reset():
    return


@blueprint.route('/hook', methods=['POST'])
def hook():
    # data = request.get_json()
    # assert data['api_version'] == STRIPE_API_VERSION

    # tablenames = {m.__tablename__: m for c, m in STRIPE_MODELS.items() \
    #     if isinstance(m, sqlalchemy.ext.declarative.api.DeclarativeMeta)}
    # obj_json = data['data']['object']
    # obj_type = obj_json['object']

    # if obj_type in tablenames:
    #     model = tablenames[obj_type]
    #     event_type = data['type'].split('.')
    #     i = session.query(model).get(obj_json['id'])

    #     if event_type[-1] == 'deleted':
    #         i.delete()
    #     elif event_type[-1] == 'created':
    #         # create object
    #         i = model()

    #     i.load_json(obj_json)
    #     session.add(i)

    # session.commit()
    return '', 201
