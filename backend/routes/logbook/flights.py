"""GlideLog — flights API endpoints."""
import logging

from flask import jsonify, request
from flask_login import current_user

from backend.db import get_db
from backend.routes.logbook import logbook_bp
from backend.services.logbook import flights as flight_svc
from backend.utils.auth_decorators import login_required

logger = logging.getLogger(__name__)


@logbook_bp.route('/api/flights', methods=['GET'])
@login_required
def list_flights():
    db = get_db()
    page = max(1, int(request.args.get('page', 1)))
    limit = min(200, max(1, int(request.args.get('limit', 50))))
    flights, total = flight_svc.list_flights(
        db,
        current_user,
        date_from=request.args.get('date_from'),
        date_to=request.args.get('date_to'),
        aircraft_type=request.args.get('aircraft_type'),
        launch_type=request.args.get('launch_type'),
        task=request.args.get('task'),
        page=page,
        limit=limit,
    )
    return jsonify({
        'flights': [f.to_dict() for f in flights],
        'total': total,
        'page': page,
        'limit': limit,
        'pages': (total + limit - 1) // limit,
    })


@logbook_bp.route('/api/flights/<flight_id>', methods=['GET'])
@login_required
def get_flight(flight_id):
    db = get_db()
    try:
        flight = flight_svc.get_flight(db, current_user, flight_id)
        return jsonify(flight.to_dict())
    except flight_svc.FlightServiceError as e:
        return jsonify({'error': str(e)}), 404


@logbook_bp.route('/api/flights/manual', methods=['POST'])
@login_required
def create_manual_flight():
    db = get_db()
    data = request.get_json(silent=True) or {}
    try:
        flight = flight_svc.create_manual_flight(db, current_user, data)
        db.commit()
        return jsonify(flight.to_dict()), 201
    except flight_svc.FlightServiceError as e:
        db.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception:
        db.rollback()
        logger.exception('Failed to create manual flight')
        return jsonify({'error': 'Failed to create flight.'}), 500


@logbook_bp.route('/api/flights/<flight_id>', methods=['PUT'])
@login_required
def update_flight(flight_id):
    db = get_db()
    data = request.get_json(silent=True) or {}
    try:
        flight = flight_svc.update_manual_flight(db, current_user, flight_id, data)
        db.commit()
        return jsonify(flight.to_dict())
    except flight_svc.FlightServiceError as e:
        db.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception:
        db.rollback()
        logger.exception('Failed to update flight')
        return jsonify({'error': 'Failed to update flight.'}), 500


@logbook_bp.route('/api/flights/<flight_id>', methods=['DELETE'])
@login_required
def delete_flight(flight_id):
    db = get_db()
    try:
        flight_svc.delete_flight(db, current_user, flight_id)
        db.commit()
        return '', 204
    except flight_svc.FlightServiceError as e:
        db.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception:
        db.rollback()
        logger.exception('Failed to delete flight')
        return jsonify({'error': 'Failed to delete flight.'}), 500
