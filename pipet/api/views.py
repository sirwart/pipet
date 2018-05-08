from flask import Blueprint, request

from pipet.sources import SCHEMANAME, Event, Group, Identity, Page
from pipet.sources.api.tasks import process_event, process_page


blueprint = Blueprint(SCHEMANAME, __name__)


@blueprint.route('/identity', methods=['PUT'])
def identity():
    organization = Organization.query.filter_by(name=request.authorization.username,
                                                api_key=request.authorization.password).first()
    return


@blueprint.route('/group', methods=['PUT'])
def group():
    organization = Organization.query.filter_by(name=request.authorization.username,
                                                api_key=request.authorization.password).first()
    return


@blueprint.route('/event', methods=['POST'])
def event():
    organization = Organization.query.filter_by(name=request.authorization.username,
                                                api_key=request.authorization.password).first()
    data = request.get_json()
    process_event.delay(organization.id, data)


@blueprint.route('/page', methods=['POST'])
def page():
    organization = Organization.query.filter_by(name=request.authorization.username,
                                                api_key=request.authorization.password).first()
    data = request.get_json()
    process_event.delay(organization.id, data)
