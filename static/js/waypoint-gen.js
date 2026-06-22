/**
 * waypoint-gen.js — Waypoint Generation from selected map area.
 *
 * Integrates with window.app (SoaringCupEditor) and the main Leaflet map.
 *
 * Flow:
 *  1. User clicks "Select Area" → map enters polygon-draw mode.
 *  2. User clicks to drop vertices, then double-clicks to close the polygon.
 *  3. UI shows the selected area + type checkboxes.
 *  4. User clicks "Generate" → POST /api/waypoint-gen/generate.
 *  5. Response is merged into window.app.waypoints and updateUI() is called.
 *
 * Aviation data is fetched on-demand from OpenAIP; no local import required.
 */
(function () {
    'use strict';

    // ── State ────────────────────────────────────────────────────────────────
    let _polyLayer = null;       // L.Polygon (closed) or L.Polyline (in progress)
    let _vertexMarkers = [];     // L.CircleMarker per dropped vertex
    let _points = [];            // L.LatLng[] — vertices being placed
    let _selectedPolygon = null; // L.LatLng[] — the finalised polygon
    let _selecting = false;
    let _clickTimer = null;      // debounce so a double-click doesn't add vertices
    let _mapHandlers = null;     // { click, dblclick } bound during selection

    // ── DOM helpers ───────────────────────────────────────────────────────────
    const $ = (id) => document.getElementById(id);

    // Translate with a guaranteed fallback. window.i18n.t() returns the key
    // itself when a translation is missing, so we can't rely on `?? fallback`;
    // pass the fallback through i18n's own (key, fallback, params) signature and
    // still cover the case where i18n hasn't loaded at all.
    function _t(key, fallback, params) {
        if (window.i18n && typeof window.i18n.t === 'function') {
            return window.i18n.t(key, fallback, params);
        }
        let val = fallback;
        if (params) {
            Object.entries(params).forEach(([k, v]) => {
                val = val.replace(new RegExp(`\\{${k}\\}`, 'g'), v);
            });
        }
        return val;
    }

    function _setStatus(msg, variant) {
        const el = $('wpgen-status');
        if (!el) return;
        el.style.display = msg ? 'block' : 'none';
        el.innerHTML = msg || '';
        el.className = 'wpgen-status' + (variant ? ` wpgen-status--${variant}` : '');
    }

    function _setGenerateEnabled() {
        const btn = $('wpgen-generate-btn');
        if (!btn) return;
        const hasArea = !!_selectedPolygon;
        const hasType = [
            'wpgen-airports', 'wpgen-outlandings', 'wpgen-obstacles',
            'wpgen-navaids', 'wpgen-hotspots', 'wpgen-hang-glidings', 'wpgen-reporting-points',
            'wpgen-cities', 'wpgen-towns', 'wpgen-villages',
        ].some((id) => {
            const el = $(id);
            return el && el.checked;
        });
        btn.disabled = !(hasArea && hasType);
    }

    // ── Map area selection ────────────────────────────────────────────────────
    function _getMap() {
        return window.app && window.app.map;
    }

    function _formatPolygon(points) {
        return _t('wpgen.area_points', '{n}-point area', { n: points.length });
    }

    function _updateAreaUI() {
        const areaInfo = $('wpgen-area-info');
        const areaText = $('wpgen-area-text');
        const selectBtn = $('wpgen-select-area-btn');

        if (_selecting) {
            // While drawing, the button doubles as a "Finish" action.
            if (areaInfo) areaInfo.style.display = 'none';
            if (selectBtn) selectBtn.innerHTML = `<i class="fas fa-check" slot="prefix"></i> ${_t('wpgen.finish_area', 'Finish')}`;
        } else if (_selectedPolygon) {
            if (areaInfo) areaInfo.style.display = 'flex';
            if (areaText) areaText.textContent = _formatPolygon(_selectedPolygon);
            if (selectBtn) selectBtn.textContent = _t('wpgen.change_area', 'Change Area');
        } else {
            if (areaInfo) areaInfo.style.display = 'none';
            if (selectBtn) selectBtn.innerHTML = `<i class="fas fa-draw-polygon" slot="prefix"></i> ${_t('wpgen.select_area', 'Select Area')}`;
        }
        _setGenerateEnabled();
    }

    // Remove all drawing layers (polygon + vertex markers) from the map.
    function _removeLayers() {
        const map = _getMap();
        if (!map) return;
        if (_polyLayer) { map.removeLayer(_polyLayer); _polyLayer = null; }
        _vertexMarkers.forEach((m) => map.removeLayer(m));
        _vertexMarkers = [];
    }

    // Redraw the in-progress shape: a polyline for < 3 points, a polygon after.
    function _redrawDraft() {
        const map = _getMap();
        if (!map) return;
        const latlngs = _points.slice();
        if (_polyLayer) { map.removeLayer(_polyLayer); _polyLayer = null; }
        if (latlngs.length >= 2) {
            const opts = { interactive: false, color: '#2563eb', weight: 2, dashArray: '4 4', fillOpacity: 0.15 };
            _polyLayer = (latlngs.length >= 3 ? L.polygon(latlngs, opts) : L.polyline(latlngs, opts)).addTo(map);
        }
    }

    function _addVertex(latlng) {
        const map = _getMap();
        if (!map) return;
        _points.push(latlng);
        const marker = L.circleMarker(latlng, {
            radius: 4, color: '#2563eb', weight: 2, fillColor: '#fff', fillOpacity: 1, interactive: false,
        }).addTo(map);
        _vertexMarkers.push(marker);
        _redrawDraft();
        const ready = _points.length >= 3;
        const hint = ready
            ? _t('wpgen.select_hint_ready', 'Click to add more points, or click Finish / double-click to close ({n} so far).', { n: _points.length })
            : _t('wpgen.select_hint', 'Click to add points ({n} so far). At least 3 needed.', { n: _points.length });
        _setStatus(`<i class="fas fa-draw-polygon"></i> ${hint}`, 'info');
    }

    function _exitSelectionMode() {
        const map = _getMap();
        _selecting = false;
        if (_clickTimer) { clearTimeout(_clickTimer); _clickTimer = null; }
        if (map && _mapHandlers) {
            map.off('click', _mapHandlers.click);
            map.off('dblclick', _mapHandlers.dblclick);
            map.getContainer().style.cursor = '';
            map.getContainer().classList.remove('wpgen-selecting');
            map.doubleClickZoom.enable();
        }
        _mapHandlers = null;
    }

    function _clearSelection() {
        _exitSelectionMode();
        _removeLayers();
        _points = [];
        _selectedPolygon = null;
        _updateAreaUI();
        _setStatus('', '');
    }

    function _startAreaSelection() {
        const map = _getMap();
        if (!map || _selecting) return;

        // Reset any previous drawing/selection before starting fresh.
        _removeLayers();
        _points = [];
        _selectedPolygon = null;

        _selecting = true;
        map.getContainer().style.cursor = 'crosshair';
        map.getContainer().classList.add('wpgen-selecting');
        map.doubleClickZoom.disable();
        _updateAreaUI();  // switch the button to "Finish"

        // A double-click fires two `click` events before `dblclick`; debounce the
        // clicks so the closing double-click doesn't drop two stray vertices.
        const onClick = (e) => {
            if (_clickTimer) { clearTimeout(_clickTimer); _clickTimer = null; }
            const latlng = e.latlng;
            _clickTimer = setTimeout(() => {
                _clickTimer = null;
                _addVertex(latlng);
            }, 250);
        };
        const onDblClick = () => {
            if (_clickTimer) { clearTimeout(_clickTimer); _clickTimer = null; }
            _finishSelection();
        };

        _mapHandlers = { click: onClick, dblclick: onDblClick };
        map.on('click', onClick);
        map.on('dblclick', onDblClick);

        const hint = _t('wpgen.select_start', 'Click on the map to add area points (min 3), then click Finish or double-click.');
        _setStatus(`<i class="fas fa-draw-polygon"></i> ${hint}`, 'info');
    }

    // Button dispatcher: starts a new selection, or finishes the one in progress.
    function _toggleAreaSelection() {
        if (_selecting) {
            _finishSelection();
        } else {
            _startAreaSelection();
        }
    }

    function _finishSelection() {
        if (_points.length < 3) {
            const msg = _t('wpgen.need_three', 'An area needs at least 3 points.');
            _exitSelectionMode();
            _removeLayers();
            _points = [];
            _selectedPolygon = null;
            _updateAreaUI();
            _setStatus(`<i class="fas fa-exclamation-circle"></i> ${msg}`, 'error');
            return;
        }

        _selectedPolygon = _points.slice();
        _exitSelectionMode();
        // Replace the dashed draft with a solid finalised polygon.
        _removeLayers();
        const map = _getMap();
        if (map) {
            _polyLayer = L.polygon(_selectedPolygon, {
                interactive: false, color: '#2563eb', weight: 2, fillOpacity: 0.15,
            }).addTo(map);
        }
        _points = [];
        _updateAreaUI();
        _setStatus('', '');
    }

    // ── Generate ──────────────────────────────────────────────────────────────
    async function _generate() {
        if (!_selectedPolygon) { _setStatus('Select an area on the map first.', 'error'); return; }

        const types = [];
        const typeMap = {
            'wpgen-airports': 'airports',
            'wpgen-outlandings': 'outlandings',
            'wpgen-obstacles': 'obstacles',
            'wpgen-navaids': 'navaids',
            'wpgen-hotspots': 'hotspots',
            'wpgen-hang-glidings': 'hang_glidings',
            'wpgen-reporting-points': 'reporting_points',
            'wpgen-cities': 'cities',
            'wpgen-towns': 'towns',
            'wpgen-villages': 'villages',
        };
        for (const [id, val] of Object.entries(typeMap)) {
            const el = $(id);
            if (el && el.checked) types.push(val);
        }
        if (!types.length) { _setStatus('Select at least one waypoint type.', 'error'); return; }

        const btn = $('wpgen-generate-btn');
        if (btn) { btn.loading = true; btn.disabled = true; }
        _setStatus('<i class="fas fa-spinner fa-spin"></i> Generating waypoints…', 'info');

        const body = {
            polygon: _selectedPolygon.map((p) => [p.lat, p.lng]),
            types,
        };

        try {
            const res = await fetch('/api/waypoint-gen/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            const data = await res.json();

            if (!data.success) {
                _setStatus(`<i class="fas fa-exclamation-circle"></i> ${data.error || 'Generation failed.'}`, 'error');
                return;
            }

            // Merge generated waypoints into existing client-side waypoints,
            // de-duplicating by name+lat+lon so re-generating the same area is safe.
            if (window.app) {
                const existing = window.app.waypoints || [];
                const existingKeys = new Set(
                    existing.map(wp => `${wp.name}|${(+wp.latitude).toFixed(5)}|${(+wp.longitude).toFixed(5)}`)
                );
                const incoming = data.waypoints || [];
                const newOnly = incoming.filter(
                    wp => !existingKeys.has(`${wp.name}|${(+wp.latitude).toFixed(5)}|${(+wp.longitude).toFixed(5)}`)
                );
                window.app.waypoints = existing.concat(newOnly);
                window.app.updateUI(true);
                data.added = newOnly.length;
            }

            // Build result message
            const src = data.sources || {};
            const parts = [];
            if (src.aviation) parts.push(`${src.aviation} aviation`);
            if (src.osm) parts.push(`${src.osm} OSM places`);
            const detail = parts.length ? ` (${parts.join(', ')})` : '';
            let msg = `<i class="fas fa-check-circle"></i> Added ${data.added} waypoint${data.added !== 1 ? 's' : ''}${detail}.`;

            if (data.warnings && data.warnings.length) {
                msg += `<br><small><i class="fas fa-exclamation-triangle"></i> ${data.warnings.join(' ')}</small>`;
            }
            _setStatus(msg, 'success');
        } catch (err) {
            _setStatus(`<i class="fas fa-exclamation-circle"></i> Error: ${err.message}`, 'error');
        } finally {
            if (btn) { btn.loading = false; btn.disabled = false; }
            _setGenerateEnabled();
        }
    }

    // ── Card collapse ─────────────────────────────────────────────────────────
    function _setupCardCollapse() {
        const btn = $('wpgen-card-toggle');
        const body = $('wpgen-card-body');
        if (!btn || !body) return;
        let collapsed = false;
        btn.addEventListener('click', () => {
            collapsed = !collapsed;
            body.style.display = collapsed ? 'none' : '';
            btn.name = collapsed ? 'chevron-right' : 'chevron-down';
        });
    }

    // ── Init ──────────────────────────────────────────────────────────────────
    function init() {
        // Setup collapse
        _setupCardCollapse();

        // Select Area button
        const selectBtn = $('wpgen-select-area-btn');
        if (selectBtn) {
            selectBtn.addEventListener('click', _toggleAreaSelection);
        }

        // Clear area button
        const clearBtn = $('wpgen-clear-area-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', _clearSelection);
        }

        // Generate button
        const genBtn = $('wpgen-generate-btn');
        if (genBtn) {
            genBtn.addEventListener('click', _generate);
        }

        // Update generate button state when checkboxes change
        [
            'wpgen-airports', 'wpgen-outlandings', 'wpgen-obstacles',
            'wpgen-navaids', 'wpgen-hotspots', 'wpgen-hang-glidings', 'wpgen-reporting-points',
            'wpgen-cities', 'wpgen-towns', 'wpgen-villages',
        ].forEach((id) => {
            const el = $(id);
            if (el) el.addEventListener('sl-change', _setGenerateEnabled);
        });
    }

    // Wait for DOM + Shoelace to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        // Also wait a tick for Shoelace custom elements to upgrade
        requestAnimationFrame(init);
    }

    // Expose for debugging
    window.waypointGen = { clearSelection: _clearSelection };
})();
