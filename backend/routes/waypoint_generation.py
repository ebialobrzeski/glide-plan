"""Waypoint Generation routes — /api/waypoint-gen/*

Endpoints:
  POST /api/waypoint-gen/generate    — generate waypoints for a bbox + type list
"""
from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request, session

from backend.db import get_db
from backend.services import waypoint_generation_service as svc

logger = logging.getLogger(__name__)

waypoint_gen_bp = Blueprint('waypoint_gen', __name__, url_prefix='/api/waypoint-gen')


# ── routes ────────────────────────────────────────────────────────────────────

@waypoint_gen_bp.route('/generate', methods=['POST'])
def generate():
    """Generate waypoints for a custom map area.

    Request JSON (either ``polygon`` or ``bbox`` must be supplied)::
        {
            "polygon": [[lat, lon], [lat, lon], [lat, lon], ...],
            "bbox": {"min_lat": float, "max_lat": float,
                     "min_lon": float, "max_lon": float},
            "types": ["airports", "outlandings", "obstacles",
                      "cities", "towns", "villages"]
        }

    When ``polygon`` is given (a list of at least 3 ``[lat, lon]`` vertices), the
    external APIs are queried by the polygon's bounding box and the results are
    filtered down to points that fall inside the polygon. ``bbox`` is accepted as
    a fallback for a plain rectangular selection.

    On success the new waypoints are MERGED into the current session and the
    full updated waypoint list is returned so the frontend can replace
    window.app.waypoints in one step.
    """
    body = request.get_json(silent=True) or {}
    types = body.get('types', [])
    polygon_raw = body.get('polygon')
    polygon: list[tuple[float, float]] | None = None

    if polygon_raw is not None:
        try:
            polygon = [(float(p[0]), float(p[1])) for p in polygon_raw]
        except (TypeError, ValueError, IndexError):
            return jsonify({'success': False, 'error': 'Invalid polygon. Provide a list of [lat, lon] points.'}), 400
        if len(polygon) < 3:
            return jsonify({'success': False, 'error': 'A polygon needs at least 3 points.'}), 400
        lats = [p[0] for p in polygon]
        lons = [p[1] for p in polygon]
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)
    else:
        bbox = body.get('bbox', {})
        try:
            min_lat = float(bbox['min_lat'])
            max_lat = float(bbox['max_lat'])
            min_lon = float(bbox['min_lon'])
            max_lon = float(bbox['max_lon'])
        except (KeyError, TypeError, ValueError):
            return jsonify({'success': False, 'error': 'Invalid area. Provide a polygon or a bbox (min_lat, max_lat, min_lon, max_lon).'}), 400

    if not isinstance(types, list) or not types:
        return jsonify({'success': False, 'error': 'types must be a non-empty list.'}), 400

    db = get_db()
    result = svc.generate_waypoints(db, min_lat, max_lat, min_lon, max_lon, types, polygon=polygon)

    return jsonify({
        'success': True,
        'added': len(result['waypoints']),
        'sources': result['sources'],
        'warnings': result.get('warnings', []),
        'waypoints': [wp.to_dict() for wp in result['waypoints']],
    })
