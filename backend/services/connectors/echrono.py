"""EchronoConnector — fetches flight data from ab-pilot.echronometraz.pl.

The connector first attempts to retrieve a JSON response from the API.
If the server returns HTML (legacy), it falls back to HTML table parsing.

Expected JSON record format (single flight):
{
    "external_id": "71449",
    "list_no": "2025/G/009",
    "pdt_no": "2025/3788/1",
    "date": "2025-04-26",
    "aircraft": "SZD-50-3 SP-3788",
    "pilot": "Białobrzeski Emil",
    "instructor": "Wiśniewski Dariusz",
    "task": "SPL / I - 1",
    "launch_type": "W",
    "takeoff_airport": "EPBK",
    "takeoff_time": "10:10",
    "landing_airport": "EPBK",
    "landing_time": "10:21",
    "flight_time": "00:11",
    "landings": 1,
    "is_instructor": true,
    "is_settled": true,
    "price": 118.70,
    "price_breakdown": {
        "launch_price": 55.00,
        "flight_time_cost": 63.70,
        "instructor_fee": 36.20,
        "resource_fee": 27.50
    },
    "crew": {
        "first_cabin": "Białobrzeski Emil",
        "second_cabin": "Wiśniewski Dariusz",
        "payer": "Białobrzeski Emil",
        "winch_operator": "Kalinowski Sławomir"
    }
}
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import Optional

import httpx
from bs4 import BeautifulSoup, NavigableString, Tag

from backend.services.connectors.base import BaseConnector

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = 'https://ab-pilot.echronometraz.pl'
_LOGIN_PATH = '/index.php'
_FLIGHTS_PATH = '/index.php'


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _parse_time(value: str) -> Optional[str]:
    """Normalise an HH:MM[:SS] string to 'HH:MM'.  Returns None on failure."""
    if not value:
        return None
    value = value.strip()
    if re.match(r'^\d{1,2}:\d{2}', value):
        return value[:5].zfill(5)
    return None


def _hhmm_to_minutes(value: str) -> Optional[int]:
    """Convert 'HH:MM' or 'MM:SS'-style string to total minutes."""
    if not value:
        return None
    value = value.strip()
    m = re.match(r'^(\d+):(\d{2})$', value)
    if not m:
        return None
    return int(m.group(1)) * 60 + int(m.group(2))


def _split_aircraft(aircraft_str: str) -> tuple[str, str]:
    """Split 'SZD-50-3 SP-3788' into (aircraft_type, aircraft_reg).

    The registration starts at the LETTERS-ALPHANUMERIC token (e.g. SP-3788,
    D-KOOL) and extends to the end of the string, including any short uppercase
    suffix that follows (e.g. 'SP-3696 AB').
    """
    if not aircraft_str:
        return '', ''
    aircraft_str = aircraft_str.strip()
    # Match a registration-like token optionally followed by a short uppercase
    # suffix (e.g. "SP-3696 AB").  The suffix handles cases where the system
    # appends a cabin/variant code after the main registration code.
    reg_match = re.search(r'\b([A-Z]{1,3}-[A-Z0-9]{3,6}(?:\s+[A-Z]{1,4})?)\s*$', aircraft_str)
    if reg_match:
        aircraft_type = aircraft_str[: reg_match.start()].strip()
        aircraft_reg = reg_match.group(1)
    else:
        parts = aircraft_str.rsplit(' ', 1)
        aircraft_type = parts[0].strip() if len(parts) == 2 else aircraft_str
        aircraft_reg = parts[1].strip() if len(parts) == 2 else ''
    return aircraft_type, aircraft_reg


# ---------------------------------------------------------------------------
# JSON response parser
# ---------------------------------------------------------------------------

def _normalize_json_flight(record: dict) -> dict:
    """Normalise a single JSON flight record to the internal canonical format.

    The canonical format mirrors the output of the HTML parser so that
    sync._build_flight_row() can process both without branching.
    """
    # Aircraft: split combined string if needed.
    # Some echrono records use a single 'aircraft' field ("SZD-50-3 SP-3788"),
    # others supply 'aircraft_type' and 'aircraft_reg' separately.  In the
    # latter case the type field may contain an embedded registration
    # (e.g. aircraft_type="SZD-51-1 SP-3696", aircraft_reg="AB"), so we
    # re-split only when the type field contains a registration-like token
    # (identified by a LETTERS-DIGITS dash pattern).
    _REG_PATTERN = re.compile(r'\b[A-Z]{1,3}-[A-Z0-9]{3,6}\b')
    if 'aircraft' in record:
        aircraft_type, aircraft_reg = _split_aircraft(record['aircraft'])
    else:
        raw_type = record.get('aircraft_type', '')
        raw_reg  = record.get('aircraft_reg', '')
        if _REG_PATTERN.search(raw_type):
            # type field has an embedded registration — re-split and merge suffix
            aircraft_type, embedded_reg = _split_aircraft(raw_type)
            aircraft_reg = (embedded_reg + ' ' + raw_reg).strip() if raw_reg else embedded_reg
        else:
            aircraft_type = raw_type
            aircraft_reg  = raw_reg
        logger.debug(
            'eChronometraż aircraft: raw_type=%r raw_reg=%r -> type=%r reg=%r',
            raw_type, raw_reg, aircraft_type, aircraft_reg,
        )

    # Flight time: convert HH:MM → minutes if the integer form is missing
    if 'flight_time_min' in record:
        flight_time_min = record['flight_time_min']
    elif 'flight_time' in record:
        flight_time_min = _hhmm_to_minutes(record['flight_time'])
    else:
        flight_time_min = None

    # Price: may be a float directly or a string
    price: Optional[float] = None
    raw_price = record.get('price')
    if raw_price is not None:
        try:
            price = float(raw_price)
        except (TypeError, ValueError):
            pass

    price_breakdown: dict = record.get('price_breakdown') or {}
    crew: dict = record.get('crew') or {}

    flight = {
        'external_id': str(record['external_id']) if record.get('external_id') is not None else None,
        'list_no':      record.get('list_no'),
        'pdt_no':       record.get('pdt_no'),
        'date':         record.get('date'),
        'aircraft_type': aircraft_type or None,
        'aircraft_reg':  aircraft_reg or None,
        'pilot':        record.get('pilot') or None,
        'instructor':   record.get('instructor') or None,
        'task':         record.get('task') or None,
        'launch_type':  record.get('launch_type') or None,
        'takeoff_airport':  record.get('takeoff_airport') or None,
        'takeoff_time':     _parse_time(record.get('takeoff_time', '')),
        'landing_airport':  record.get('landing_airport') or None,
        'landing_time':     _parse_time(record.get('landing_time', '')),
        'flight_time_min':  flight_time_min,
        'landings':         int(record['landings']) if record.get('landings') is not None else 1,
        'is_instructor':    bool(record.get('is_instructor', False)),
        'is_settled':       bool(record.get('is_settled', False)),
        'price':            price,
        'price_breakdown':  price_breakdown,
        'crew':             crew,
    }
    # Preserve the full original record as raw_data
    flight['raw_data'] = {k: v for k, v in flight.items() if k != 'raw_data'}
    return flight


def parse_flights_json(data) -> list[dict]:
    """Parse a JSON payload (list or dict with 'flights' key) into normalised records."""
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        records = data.get('flights') or data.get('data') or []
    else:
        return []

    flights: list[dict] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        try:
            flights.append(_normalize_json_flight(record))
        except Exception:
            logger.exception('eChronometraż JSON: failed to normalise record %r', record)
    logger.info('eChronometraż JSON parser: normalised %d flights', len(flights))
    return flights


# ---------------------------------------------------------------------------
# HTML response parser (legacy fallback)
# ---------------------------------------------------------------------------

def _clean_cell(td) -> str:
    """Extract meaningful text from a cell, stripping embedded edit buttons/forms."""
    parts: list[str] = []
    for child in td.children:
        if isinstance(child, NavigableString):
            t = str(child).strip()
            if t:
                parts.append(t)
        elif isinstance(child, Tag):
            if child.name in ('button', 'form', 'input', 'script', 'style'):
                continue
            inner = _clean_cell(child)
            if inner:
                parts.append(inner)
    return ' '.join(parts).strip()


def _raw_text(cells: list, idx: int) -> str:
    if idx < len(cells):
        return cells[idx].get_text(strip=True)
    return ''


def _cell(cells: list, idx: int) -> str:
    if idx < len(cells):
        return _clean_cell(cells[idx])
    return ''


def parse_flights_html(html: str) -> list[dict]:
    """
    Parse the flights HTML table from eChronometraż.

    Observed column layout (0-based):
      0  – link cell  (external_id extracted from href)
      1  – empty / status flag
      2  – row counter
      3  – list_no      e.g. "2025/G/009"
      4  – pdt_no       e.g. "2025/3788/1"
      5  – date         e.g. "2025-04-26"
      6  – aircraft     e.g. "SZD-50-3 SP-3788"
      7  – pilot
      8  – instructor
      9  – task         e.g. "SPL / I - 1"
      10 – launch_type  e.g. "W"
      11 – takeoff_airport
      12 – takeoff_time
      13 – landing_airport
      14 – landing_time
      15 – flight_time  e.g. "00:11"
      16 – landings
      17 – is_instructor flag  ("Tak"/"Nie")
      18 – price  ("Cena")
      (is_settled derived from column 1 icon; crew/price_breakdown from tooltip)
    """
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', class_='table')
    if not table:
        logger.warning('eChronometraż HTML parser: no <table class="table"> found')
        return []

    flights: list[dict] = []
    rows = table.find_all('tr')

    for row in rows:
        cells = row.find_all('td')
        if len(cells) < 6:
            continue

        # External ID from href in first cell
        first_link = cells[0].find('a', href=True)
        if not first_link:
            continue
        m = re.search(r'flightShow&id=(\d+)', first_link.get('href', ''))
        if not m:
            continue
        external_id = m.group(1)

        # Parse <tr title="..."> tooltip — contains price breakdown and crew
        price_raw: Optional[float] = None
        price_breakdown: dict = {}
        crew: dict = {}
        is_settled = False

        title_html = row.get('title', '')
        if title_html:
            tsoup = BeautifulSoup(title_html, 'html.parser')
            title_text = tsoup.get_text(' ', strip=True)

            # Total price: "Sumaryczna opłata za lot: X + Y + Z + = TOTAL"
            m_total = re.search(
                r'Sumaryczna op[łl]ata za lot\s*:.*?=\s*([\d]+(?:[.,]\d+)?)',
                title_text, re.DOTALL | re.IGNORECASE,
            )
            if m_total:
                try:
                    price_raw = float(m_total.group(1).replace(',', '.'))
                except ValueError:
                    pass

            # Price breakdown components
            def _re_price(pat: str) -> Optional[float]:
                mx = re.search(pat, title_text, re.IGNORECASE | re.DOTALL)
                if mx:
                    try:
                        return float(mx.group(1).replace(',', '.'))
                    except ValueError:
                        pass
                return None

            launch_price   = _re_price(r'Cena startu\s*:\s*([\d]+(?:[.,]\d+)?)')
            flight_cost    = _re_price(r'Sumaryczna op[łl]ata za czas lotu\s*(?:lot)?\s*:\s*([\d]+(?:[.,]\d+)?)')
            instructor_fee = _re_price(r'Op[łl]ata za instruktora\s+Razem\s*:\s*([\d]+(?:[.,]\d+)?)')
            resource_fee   = _re_price(r'Op[łl]ata resursowa\s+Razem\s*:\s*([\d]+(?:[.,]\d+)?)')

            price_breakdown = {k: v for k, v in {
                'launch_price':     launch_price,
                'flight_time_cost': flight_cost,
                'instructor_fee':   instructor_fee,
                'resource_fee':     resource_fee,
            }.items() if v is not None}

            # Crew members from tooltip HTML
            def _re_crew(label: str) -> Optional[str]:
                mc = re.search(
                    r'<b[^>]*>\s*' + re.escape(label) + r'\s*</b>\s*:?\s*([^<\n]+)',
                    title_html, re.IGNORECASE,
                )
                if mc:
                    val = mc.group(1).strip().strip(':').strip()
                    return val if val else None
                return None

            first_cabin  = _re_crew('Pierwsza kabina')
            second_cabin = _re_crew('Druga kabina (dow') or _re_crew('Druga kabina')
            payer        = _re_crew('P&#322;atnik') or _re_crew('Płatnik')
            winch_op     = _re_crew('Wyci&#261;garkowy') or _re_crew('Wyciągarkowy')

            crew = {k: v for k, v in {
                'first_cabin':    first_cabin,
                'second_cabin':   second_cabin,
                'payer':          payer,
                'winch_operator': winch_op,
            }.items() if v is not None}

        # is_settled: column 1 contains a check-circle icon when settled
        is_settled_cell = cells[1] if len(cells) > 1 else None
        if is_settled_cell:
            cell_html = str(is_settled_cell)
            is_settled = bool(
                re.search(r'check|fa-check|rozl|settled', cell_html, re.IGNORECASE)
            )

        # Column extraction
        list_no         = _raw_text(cells, 3)
        pdt_no          = _raw_text(cells, 4)
        date_str        = _raw_text(cells, 5)
        aircraft_full   = _cell(cells, 6)
        pilot           = _cell(cells, 7)
        instructor      = _cell(cells, 8)
        task            = _cell(cells, 9)
        launch_type     = _raw_text(cells, 10)
        takeoff_airport = _raw_text(cells, 11)
        takeoff_time_str= _raw_text(cells, 12)
        landing_airport = _raw_text(cells, 13)
        landing_time_str= _raw_text(cells, 14)
        flight_time_str = _raw_text(cells, 15)
        landings_str    = _raw_text(cells, 16)
        is_instructor_str = _raw_text(cells, 17)
        price_str       = _raw_text(cells, 18) if len(cells) > 18 else ''

        # Parse date
        parsed_date = ''
        for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%d-%m-%Y'):
            try:
                parsed_date = datetime.strptime(date_str.strip(), fmt).date().isoformat()
                break
            except ValueError:
                continue
        if not parsed_date:
            logger.debug('eChronometraż HTML: unparseable date %r for flight %s', date_str, external_id)

        # Aircraft type + registration
        aircraft_type, aircraft_reg = _split_aircraft(aircraft_full)

        # Numeric fields
        try:
            landings = int(landings_str)
        except (ValueError, TypeError):
            landings = 1

        # Price fallback: try cell text if tooltip had nothing
        if price_raw is None and price_str:
            cleaned = re.sub(r'[^\d.,]', '', price_str.replace('\xa0', '').replace('\u202f', '')).replace(',', '.')
            if cleaned:
                try:
                    price_raw = float(cleaned)
                except ValueError:
                    pass

        flight = {
            'external_id':   external_id,
            'list_no':       list_no,
            'pdt_no':        pdt_no,
            'date':          parsed_date,
            'aircraft_type': aircraft_type or None,
            'aircraft_reg':  aircraft_reg or None,
            'pilot':         pilot or None,
            'instructor':    instructor or None,
            'task':          task or None,
            'launch_type':   launch_type or None,
            'takeoff_airport':  takeoff_airport or None,
            'takeoff_time':     _parse_time(takeoff_time_str),
            'landing_airport':  landing_airport or None,
            'landing_time':     _parse_time(landing_time_str),
            'flight_time_min':  _hhmm_to_minutes(flight_time_str),
            'landings':         landings,
            'is_instructor':    is_instructor_str.lower() in ('tak', 'yes', '1', 'true'),
            'is_settled':       is_settled,
            'price':            price_raw,
            'price_breakdown':  price_breakdown,
            'crew':             crew,
        }
        flight['raw_data'] = {k: v for k, v in flight.items() if k != 'raw_data'}
        flights.append(flight)

    logger.info('eChronometraż HTML parser: found %d flights', len(flights))
    return flights


# ---------------------------------------------------------------------------
# Connector class
# ---------------------------------------------------------------------------

class EchronoConnector(BaseConnector):
    """Connector for the eChronometraż flight logging system.

    Tries the JSON API first.  Falls back to HTML table scraping if the
    response is not valid JSON.
    """

    def __init__(self, db_record) -> None:
        super().__init__(db_record)
        self._base_url = (db_record.base_url or _DEFAULT_BASE_URL).rstrip('/')

    def _login(self) -> Optional[str]:
        login = self._decrypt(self._record.login_encrypted)
        password = self._decrypt(self._record.password_encrypted)
        if not login or not password:
            logger.warning('eChronometraż: missing credentials for connector %s', self._record.id)
            return None

        try:
            with httpx.Client(follow_redirects=False, timeout=30) as client:
                resp = client.post(
                    self._base_url + _LOGIN_PATH,
                    data={'login': login, 'password': password},
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                )
                phpsessid = resp.cookies.get('PHPSESSID')
                if phpsessid:
                    return phpsessid
                logger.warning(
                    'eChronometraż login: no PHPSESSID cookie (status=%s)', resp.status_code
                )
                return None
        except httpx.RequestError as exc:
            logger.error('eChronometraż login request failed: %s', exc)
            return None

    def test_connection(self) -> bool:
        return self._login() is not None

    def fetch_flights(self, date_from: date, date_to: date) -> list[dict]:
        phpsessid = self._login()
        if not phpsessid:
            raise RuntimeError('eChronometraż login failed — check credentials')

        request_params = {'action': 'personel', 'start': 'loty'}
        request_data = {
            'filters[perChrList][dateOd]': date_from.isoformat(),
            'filters[perChrList][dateDo]': date_to.isoformat(),
        }
        headers_common = {
            'Cookie': f'PHPSESSID={phpsessid}',
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        try:
            with httpx.Client(follow_redirects=True, timeout=60) as client:
                # Try JSON API first
                resp = client.post(
                    self._base_url + _FLIGHTS_PATH,
                    params=request_params,
                    data=request_data,
                    headers={**headers_common, 'Accept': 'application/json'},
                )
                resp.raise_for_status()

                content_type = resp.headers.get('content-type', '')
                if 'application/json' in content_type:
                    try:
                        data = resp.json()
                        flights = parse_flights_json(data)
                        if flights:
                            return flights
                        # Empty JSON list — might still be valid (no flights in range)
                        if isinstance(data, (list, dict)):
                            return flights
                    except Exception:
                        logger.warning('eChronometraż: JSON parse failed, falling back to HTML')

                # Fall back to HTML scraping
                return parse_flights_html(resp.text)

        except httpx.RequestError as exc:
            raise RuntimeError(f'eChronometraż fetch failed: {exc}') from exc
