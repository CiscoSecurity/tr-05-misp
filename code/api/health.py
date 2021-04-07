from api.utils import get_jwt, jsonify_data
from flask import Blueprint

health_api = Blueprint('health', __name__)


@health_api.route('/health', methods=['POST'])
def health():
    _ = get_jwt()
    return jsonify_data({'status': 'ok'})
