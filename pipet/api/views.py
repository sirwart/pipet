from flask import Blueprint

from pipet.sources import SCHEMANAME

blueprint = Blueprint(SCHEMANAME, __name__)


@blueprint.route('/')
def index():
    return None
