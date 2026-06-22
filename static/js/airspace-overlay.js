/**
 * airspace-overlay.js — reusable airspace fetch + render overlay for a Leaflet map.
 *
 * Encapsulates everything the airspace feature needs so it can be attached to
 * any map (the Task Planner map and the main Map View both use it):
 *   • fetch zones from OpenAIP for the current map bounds (/api/airspace/openaip)
 *   • load zones from a local OpenAir (.txt/.openair/.air) file
 *   • an altitude band filter (min/max sliders)
 *   • rendering with class-based colours and a hover tooltip
 *   • clearing
 *
 * Usage:
 *   const overlay = new AirspaceOverlay({
 *       getMap: () => myLeafletMap,
 *       layer:  existingLayerGroup,      // optional — controls z-order
 *       ids: { fetchBtn, openBtn, fileInput, clearBtn, filterPanel,
 *              fileName, count, altMin, altMax, altLabel, altFill },
 *   });
 *   overlay.bindEvents();
 */
(function () {
    'use strict';

    const SLIDER_MIN = 0;
    const SLIDER_MAX = 25000;

    class AirspaceOverlay {
        constructor({ getMap, layer = null, isReady = null, ids = {} }) {
            this._getMap = getMap;
            this._layer = layer;
            this._isReady = isReady;
            this.ids = ids;

            this.airspaces = [];        // parsed/loaded airspace objects
            this.altMin = 0;            // feet — altitude filter floor
            this.altMax = 10000;        // feet — altitude filter ceiling

            this._moveHandler = null;
            this._tooltipEl = null;
            this._mouseLeaveHandler = null;
        }

        // ── small helpers ──────────────────────────────────────────────────────
        _el(key) { return this.ids[key] ? document.getElementById(this.ids[key]) : null; }
        get map() { return this._getMap ? this._getMap() : null; }

        _ready() {
            if (!this.map) return false;
            return this._isReady ? this._isReady() : true;
        }

        _ensureLayer() {
            const map = this.map;
            if (!map) return null;
            if (!this._layer) {
                this._layer = L.layerGroup().addTo(map);
            }
            return this._layer;
        }

        /** Provide a pre-created layer group (lets the caller control z-order). */
        setLayer(layer) { this._layer = layer; }

        // ── event wiring ────────────────────────────────────────────────────────
        bindEvents() {
            const fetchBtn = this._el('fetchBtn');
            if (fetchBtn) fetchBtn.addEventListener('click', () => this.fetchOpenAip());

            const openBtn = this._el('openBtn');
            const fileInput = this._el('fileInput');
            if (openBtn && fileInput) {
                openBtn.addEventListener('click', () => fileInput.click());
                fileInput.addEventListener('change', (e) => {
                    if (e.target.files.length > 0) {
                        this.loadFile(e.target.files[0]);
                        e.target.value = '';
                    }
                });
            }

            const clearBtn = this._el('clearBtn');
            if (clearBtn) clearBtn.addEventListener('click', () => this.clear());

            const minSlider = this._el('altMin');
            const maxSlider = this._el('altMax');
            if (minSlider && maxSlider) {
                const onSlide = () => {
                    let minVal = parseInt(minSlider.value, 10);
                    let maxVal = parseInt(maxSlider.value, 10);
                    if (minVal > maxVal) {
                        // Swap so min never exceeds max
                        minSlider.value = maxVal;
                        maxSlider.value = minVal;
                        [minVal, maxVal] = [maxVal, minVal];
                    }
                    this.altMin = minVal;
                    this.altMax = maxVal;
                    const altLabel = this._el('altLabel');
                    if (altLabel) altLabel.textContent = this.formatAlt(minVal) + '–' + this.formatAlt(maxVal);
                    this._updateAltFill();
                    this.render();
                };
                minSlider.addEventListener('input', onSlide);
                maxSlider.addEventListener('input', onSlide);
            }
        }

        // ── data sources ──────────────────────────────────────────────────────
        /** Fetch airspace zones from OpenAIP for the current map view. */
        async fetchOpenAip() {
            const map = this.map;
            if (!map) return;
            const bounds = map.getBounds();
            const params = new URLSearchParams({
                south: bounds.getSouth().toFixed(4),
                west:  bounds.getWest().toFixed(4),
                north: bounds.getNorth().toFixed(4),
                east:  bounds.getEast().toFixed(4),
            });

            const btn = this._el('fetchBtn');
            if (btn) { btn.loading = true; btn.disabled = true; }

            try {
                const resp = await fetch('/api/airspace/openaip?' + params);
                if (!resp.ok) {
                    const err = await resp.json().catch(() => ({}));
                    throw new Error(err.error || resp.statusText);
                }
                const zones = await resp.json();
                this.airspaces = zones;
                this._afterLoad('OpenAIP', zones.length);
            } catch (err) {
                alert('Failed to fetch OpenAIP airspace: ' + err.message);
            } finally {
                if (btn) { btn.loading = false; btn.disabled = false; }
            }
        }

        /** Load airspace zones from a local OpenAir file. */
        loadFile(file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    this.airspaces = this.parseOpenAir(e.target.result);
                    this._afterLoad(file.name, this.airspaces.length);
                } catch (err) {
                    alert('Failed to parse airspace file: ' + err.message);
                }
            };
            reader.readAsText(file, 'UTF-8');
        }

        _afterLoad(sourceName, count) {
            const fileName = this._el('fileName');
            if (fileName) fileName.textContent = sourceName;
            const countEl = this._el('count');
            if (countEl) countEl.textContent = count + ' zones';
            const filterPanel = this._el('filterPanel');
            if (filterPanel) filterPanel.style.display = '';
            const clearBtn = this._el('clearBtn');
            if (clearBtn) clearBtn.style.display = '';
            this._updateAltFill();
            this.render();
        }

        clear() {
            this.airspaces = [];
            if (this._layer) this._layer.clearLayers();
            const map = this.map;
            if (this._moveHandler && map) {
                map.off('mousemove', this._moveHandler);
                this._moveHandler = null;
            }
            if (this._tooltipEl) this._tooltipEl.style.display = 'none';
            const filterPanel = this._el('filterPanel');
            if (filterPanel) filterPanel.style.display = 'none';
            const clearBtn = this._el('clearBtn');
            if (clearBtn) clearBtn.style.display = 'none';
        }

        // ── OpenAir parsing ──────────────────────────────────────────────────────
        parseDMSPoint(str) {
            const m = str.match(/(\d+):(\d+):(\d+(?:\.\d+)?)\s*([NS])\s+(\d+):(\d+):(\d+(?:\.\d+)?)\s*([EW])/);
            if (!m) return null;
            const lat = (parseInt(m[1]) + parseInt(m[2]) / 60 + parseFloat(m[3]) / 3600) * (m[4] === 'S' ? -1 : 1);
            const lon = (parseInt(m[5]) + parseInt(m[6]) / 60 + parseFloat(m[7]) / 3600) * (m[8] === 'W' ? -1 : 1);
            return [lat, lon];
        }

        parseAltFt(str) {
            const s = str.trim().toUpperCase();
            if (s === 'GND' || s === 'SFC' || s === 'AGL' || s === 'MSL') return 0;
            const fl = s.match(/^FL\s*(\d+)/);
            if (fl) return parseInt(fl[1]) * 100;
            const ft = s.match(/^(\d+(?:\.\d+)?)\s*FT/);
            if (ft) return Math.round(parseFloat(ft[1]));
            const mt = s.match(/^(\d+(?:\.\d+)?)\s*M(?:\s|$)/);
            if (mt) return Math.round(parseFloat(mt[1]) * 3.281);
            return 0;
        }

        parseOpenAir(text) {
            const airspaces = [];
            let cur = null;
            let cx = null;

            for (let raw of text.split('\n')) {
                const line = raw.trim();
                if (!line || line.startsWith('*')) continue;

                if (line.startsWith('AC ')) {
                    if (cur) airspaces.push(cur);
                    cur = { cls: line.slice(3).trim(), name: '', altLower: 0, altUpper: 99999, time: null, points: [], circles: [] };
                    cx = null;
                } else if (!cur) {
                    continue;
                } else if (line.startsWith('AN ')) {
                    cur.name = line.slice(3).trim();
                } else if (line.startsWith('AL ')) {
                    cur.altLower = this.parseAltFt(line.slice(3));
                } else if (line.startsWith('AH ')) {
                    cur.altUpper = this.parseAltFt(line.slice(3));
                } else if (line.startsWith('AT ')) {
                    cur.time = line.slice(3).trim();
                } else if (line.includes('X=')) {
                    cx = this.parseDMSPoint(line.slice(line.indexOf('X=') + 2));
                } else if (line.startsWith('DP ')) {
                    const ll = this.parseDMSPoint(line.slice(3));
                    if (ll) cur.points.push(ll);
                } else if (line.startsWith('DC ')) {
                    const r = parseFloat(line.slice(3));
                    if (cx && !isNaN(r)) cur.circles.push({ center: cx, radius: r * 1852 });
                }
            }
            if (cur) airspaces.push(cur);
            return airspaces;
        }

        // ── presentation ──────────────────────────────────────────────────────
        formatAlt(ft) {
            if (ft === 0) return 'GND';
            if (ft >= 1000 && ft % 100 === 0) return 'FL' + String(ft / 100).padStart(3, '0');
            return ft.toLocaleString() + ' ft';
        }

        getAirspaceStyle(cls) {
            const c = (cls || '').trim().toUpperCase();
            if (c === 'R')                         return { color: '#dc2626', fillOpacity: 0.12 };
            if (c === 'P')                         return { color: '#7f1d1d', fillOpacity: 0.18 };
            if (c === 'D')                         return { color: '#ea580c', fillOpacity: 0.12 };
            if (c === 'CTR')                       return { color: '#7c3aed', fillOpacity: 0.10 };
            if (c.includes('RMZ'))                 return { color: '#0891b2', fillOpacity: 0.08 };
            if (c.includes('TMZ'))                 return { color: '#6b7280', fillOpacity: 0.06 };
            if (c === 'W')                         return { color: '#16a34a', fillOpacity: 0.06 };
            if (c === 'C' || c === 'B')            return { color: '#2563eb', fillOpacity: 0.10 };
            if (c === 'A')                         return { color: '#1e3a8a', fillOpacity: 0.14 };
            if (c === 'E')                         return { color: '#3b82f6', fillOpacity: 0.06 };
            if (c.includes('FIR'))                 return { color: '#94a3b8', fillOpacity: 0.03 };
            return                                        { color: '#64748b', fillOpacity: 0.05 };
        }

        escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = (text == null) ? '' : String(text);
            return div.innerHTML;
        }

        _updateAltFill() {
            const fill = this._el('altFill');
            if (!fill) return;
            const lo = (this.altMin - SLIDER_MIN) / (SLIDER_MAX - SLIDER_MIN) * 100;
            const hi = (this.altMax - SLIDER_MIN) / (SLIDER_MAX - SLIDER_MIN) * 100;
            fill.style.left = lo + '%';
            fill.style.width = (hi - lo) + '%';
        }

        render() {
            const map = this.map;
            if (!this._ready()) return;
            const layer = this._ensureLayer();
            if (!layer) return;

            layer.clearLayers();
            if (this._moveHandler) {
                map.off('mousemove', this._moveHandler);
                this._moveHandler = null;
            }
            const minAlt = this.altMin;
            const maxAlt = this.altMax;

            // Create shared floating tooltip element (once)
            if (!this._tooltipEl) {
                this._tooltipEl = document.createElement('div');
                this._tooltipEl.className = 'airspace-multi-tooltip';
                this._tooltipEl.style.display = 'none';
                document.body.appendChild(this._tooltipEl);
            }
            const tooltipEl = this._tooltipEl;

            // Build flat list of {layer, as, s} for hit-testing
            const allLayers = [];

            for (const as of this.airspaces) {
                if (as.altUpper < minAlt || as.altLower > maxAlt) continue;
                const s = this.getAirspaceStyle(as.cls);
                const baseOpts = { color: s.color, weight: 1.5, opacity: 0.85, fillColor: s.color, fillOpacity: s.fillOpacity, interactive: false, bubblingMouseEvents: false };

                if (as.points.length >= 3) {
                    const lyr = L.polygon(as.points, { ...baseOpts }).addTo(layer);
                    allLayers.push({ layer: lyr, as, s });
                }
                for (const c of as.circles) {
                    const lyr = L.circle(c.center, { ...baseOpts, radius: c.radius }).addTo(layer);
                    allLayers.push({ layer: lyr, as, s });
                }
            }

            // Single map-level mousemove — hit-test every shape ourselves
            const prevHit = new Set();

            this._moveHandler = (e) => {
                const pt = e.layerPoint;
                const nowHit = new Set();
                const hitAirspaces = [];

                for (const item of allLayers) {
                    let inside = false;
                    try { inside = item.layer._containsPoint(pt); } catch (_) {}
                    if (!inside && item.layer instanceof L.Circle) {
                        inside = e.latlng.distanceTo(item.layer.getLatLng()) <= item.layer.getRadius();
                    }

                    if (inside) {
                        const id = L.stamp(item.layer);
                        nowHit.add(id);
                        hitAirspaces.push(item);
                        if (!prevHit.has(id)) {
                            item.layer.setStyle({ weight: 2.5, fillOpacity: Math.min(item.s.fillOpacity * 2.5, 0.5) });
                        }
                    }
                }

                // Un-highlight shapes we just left
                for (const item of allLayers) {
                    const id = L.stamp(item.layer);
                    if (prevHit.has(id) && !nowHit.has(id)) {
                        item.layer.setStyle({ weight: 1.5, fillOpacity: item.s.fillOpacity });
                    }
                }
                prevHit.clear();
                nowHit.forEach(id => prevHit.add(id));

                if (hitAirspaces.length === 0) {
                    tooltipEl.style.display = 'none';
                    return;
                }

                // Build tooltip content
                const parts = hitAirspaces.map(({ as }) => {
                    let row = `<div class="astt-entry">`;
                    row += `<div class="astt-name">${this.escapeHtml(as.name || as.cls)}</div>`;
                    row += `<div class="astt-meta">Class&nbsp;<strong>${this.escapeHtml(as.cls)}</strong>`;
                    if (as.type) row += `&ensp;(${this.escapeHtml(as.type)})`;
                    row += `&emsp;${this.escapeHtml(this.formatAlt(as.altLower))}&thinsp;&ndash;&thinsp;${this.escapeHtml(this.formatAlt(as.altUpper))}</div>`;
                    const flags = [];
                    if (as.requires_transponder) flags.push('XPDR');
                    if (as.requires_flight_plan) flags.push('FPL');
                    if (flags.length) row += `<div class="astt-flags">${flags.join(' · ')}</div>`;
                    if (as.time) row += `<div class="astt-time"><i class="fas fa-clock"></i> ${this.escapeHtml(as.time)}</div>`;
                    row += `</div>`;
                    return row;
                });
                tooltipEl.innerHTML = parts.join('<hr class="astt-sep">');
                tooltipEl.style.display = '';

                const mx = e.originalEvent.clientX, my = e.originalEvent.clientY;
                const pad = 14;
                const tw = tooltipEl.offsetWidth || 220, th = tooltipEl.offsetHeight || 60;
                tooltipEl.style.left = (mx + pad + tw > window.innerWidth  ? mx - tw - pad : mx + pad) + 'px';
                tooltipEl.style.top  = (my + pad + th > window.innerHeight ? my - th - pad : my + pad) + 'px';
            };

            map.on('mousemove', this._moveHandler);

            if (!this._mouseLeaveHandler) {
                this._mouseLeaveHandler = () => {
                    for (const item of allLayers) {
                        item.layer.setStyle({ weight: 1.5, fillOpacity: item.s.fillOpacity });
                    }
                    prevHit.clear();
                    if (this._tooltipEl) this._tooltipEl.style.display = 'none';
                };
                map.getContainer().addEventListener('mouseleave', this._mouseLeaveHandler);
            }
        }
    }

    window.AirspaceOverlay = AirspaceOverlay;
})();
