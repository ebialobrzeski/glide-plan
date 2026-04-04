"""EchronoConnector — scrapes ab-pilot.echronometraz.pl for flight data."""
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


def _parse_time(value: str) -> Optional[str]:
    if not value:
        return None
    value = value.strip()
    if re.match(r'^\d{1,2}:\d{2}', value):
        return value[:5].zfill(5)
    return None


def _parse_flight_time_min(value: str) -> Optional[int]:
    value = value.strip()
    m = re.match(r'^(\d+):(\d{2})$', value)
    if not m:
        return None
    return int(m.group(1)) * 60 + int(m.group(2))


def _clean_cell(td) -> str:
    """Extract meaningful text from a cell, stripping embedded edit buttons/forms."""
    parts: list[str] = []
    for child in td.children:
        if isinstance(child, NavigableString):
            t = str(child).strip()
            if t:
                parts.append(t)
        elif isinstance(child, Tag):
            # Skip form/button elements (inline edit controls)
            if child.name in ('button', 'form', 'input', 'script', 'style'):
                continue
            # Recurse into spans, b, i, etc. but not buttons
            inner = _clean_cell(child)
            if inner:
                parts.append(inner)
    return ' '.join(parts).strip()


def _raw_text(cells: list, idx: int) -> str:
    """Get plain stripped text from cell at index, or empty string."""
    if idx < len(cells):
        return cells[idx].get_text(strip=True)
    return ''


def _cell(cells: list, idx: int) -> str:
    """Get clean text (button-stripped) from cell at index."""
    if idx < len(cells):
        return _clean_cell(cells[idx])
    return ''


def parse_flights(html: str) -> list[dict]:
    """
    Parse the flights HTML table from eChronometraż.

    Observed column layout (0-based):
      0  – link cell  (external_id extracted from href, text = icon/empty)
      1  – empty / status flag
      2  – row counter or similar
      3  – list_no     e.g. "2025/G/009"
      4  – pdt_no      e.g. "2025/3788/1"
      5  – date        e.g. "2025-04-26"
      6  – aircraft    e.g. "SZD-50-3 SP-3788"  (+ inline edit buttons)
      7  – pilot       e.g. "Białobrzeski Emil"  (+ inline edit buttons)
      8  – instructor                            (+ inline edit buttons, may be empty)
      9  – task        e.g. "SPL / I - 1"
      10 – launch_type e.g. "W"
      11 – takeoff_airport
      12 – takeoff_time
      13 – landing_airport
      14 – landing_time
      15 – flight_time  e.g. "00:11"
      16 – landings
      17 – is_instructor flag  ("Tak"/"Nie")
      18 – is_settled   flag
      19 – price
    """
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', class_='table')
    if not table:
        logger.warning('eChronometraż parser: no <table class="table"> found in response')
        return []

    flights: list[dict] = []
    rows = table.find_all('tr')

    for row in rows:
        cells = row.find_all('td')
        if len(cells) < 6:
            continue  # header or empty row

        # ── External ID from href in first cell ──────────────────────────────
        first_link = cells[0].find('a', href=True)
        if not first_link:
            continue
        m = re.search(r'flightShow&id=(\d+)', first_link.get('href', ''))
        if not m:
            continue
        external_id = m.group(1)

        # ── Price / crew from <tr title="..."> ───────────────────────────────
        price_raw: Optional[float] = None
        price_breakdown: dict = {}
        crew: dict = {}
        title_html = row.get('title', '')
        if title_html:
            tsoup = BeautifulSoup(title_html, 'html.parser')
            # Use full text so number and currency symbol are always in the same string
            title_text = tsoup.get_text(' ', strip=True)
            all_prices: list[float] = []
            for m_price in re.finditer(
                r'(\d[\d\xa0\u202f ]*(?:[.,]\d{1,2})?)\s*z[łl]',
                title_text,
                re.UNICODE | re.IGNORECASE,
            ):
                cleaned = re.sub(r'[\xa0\u202f ]', '', m_price.group(1)).replace(',', '.')
                try:
                    all_prices.append(float(cleaned))
                except ValueError:
                    pass
            if all_prices:
                price_raw = max(all_prices)  # total is always the largest value

        # ── Column extraction ────────────────────────────────────────────────
        list_no    = _raw_text(cells, 3)
        pdt_no     = _raw_text(cells, 4)
        date_str   = _raw_text(cells, 5)
        aircraft_full = _cell(cells, 6)
        pilot      = _cell(cells, 7)
        instructor = _cell(cells, 8)
        task       = _cell(cells, 9)
        launch_type= _raw_text(cells, 10)
        takeoff_airport  = _raw_text(cells, 11)
        takeoff_time_str = _raw_text(cells, 12)
        landing_airport  = _raw_text(cells, 13)
        landing_time_str = _raw_text(cells, 14)
        flight_time_str  = _raw_text(cells, 15)
        landings_str     = _raw_text(cells, 16)
        is_instructor_str= _raw_text(cells, 17)
        price_str        = _raw_text(cells, 19) if len(cells) > 19 else ''

        # ── Parse date ───────────────────────────────────────────────────────
        parsed_date = ''
        for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%d-%m-%Y'):
            try:
                parsed_date = datetime.strptime(date_str.strip(), fmt).date().isoformat()
                break
            except ValueError:
                continue
        if not parsed_date:
            logger.debug('eChronometraż: could not parse date %r for flight %s', date_str, external_id)

        # ── Parse aircraft type + registration ───────────────────────────────
        aircraft_type = ''
        aircraft_reg = ''
        if aircraft_full:
            # Registration is typically the last token matching SP-XXXX or similar
            reg_match = re.search(r'\b([A-Z]{1,3}-[A-Z0-9]{3,6})\s*$', aircraft_full)
            if reg_match:
                aircraft_reg = reg_match.group(1)
                aircraft_type = aircraft_full[:reg_match.start()].strip()
            else:
                parts = aircraft_full.rsplit(' ', 1)
                aircraft_type = parts[0].strip() if len(parts) == 2 else aircraft_full
                aircraft_reg = parts[1].strip() if len(parts) == 2 else ''

        # ── Numeric fields ───────────────────────────────────────────────────
        try:
            landings = int(landings_str)
        except (ValueError, TypeError):
            landings = 1

        if price_raw is None and price_str:
            cleaned = re.sub(r'[^\d.,]', '', price_str.replace('\xa0', '').replace('\u202f', '')).replace(',', '.')
            if cleaned:
                try:
                    price_raw = float(cleaned)
                except ValueError:
                    pass

        flight = {
            'external_id': external_id,
            'list_no': list_no,
            'pdt_no': pdt_no,
            'date': parsed_date,
            'aircraft_type': aircraft_type,
            'aircraft_reg': aircraft_reg,
            'pilot': pilot or None,
            'instructor': instructor or None,
            'task': task or None,
            'launch_type': launch_type or None,
            'takeoff_airport': takeoff_airport or None,
            'takeoff_time': _parse_time(takeoff_time_str),
            'landing_airport': landing_airport or None,
            'landing_time': _parse_time(landing_time_str),
            'flight_time_min': _parse_flight_time_min(flight_time_str),
            'landings': landings,
            'is_instructor': is_instructor_str.lower() in ('tak', 'yes', '1', 'true'),
            'price': price_raw,
            'price_breakdown': price_breakdown,
            'crew': crew,
        }
        flight['raw_data'] = {k: v for k, v in flight.items() if k != 'raw_data'}
        flights.append(flight)

    logger.info('eChronometraż parser: found %d flights', len(flights))
    return flights


class EchronoConnector(BaseConnector):
    """Connector for the eChronometraż flight logging system."""

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

        try:
            with httpx.Client(follow_redirects=True, timeout=60) as client:
                resp = client.post(
                    self._base_url + _FLIGHTS_PATH,
                    params={'action': 'personel', 'start': 'loty'},
                    data={
                        'filters[perChrList][dateOd]': date_from.isoformat(),
                        'filters[perChrList][dateDo]': date_to.isoformat(),
                    },
                    headers={
                        'Cookie': f'PHPSESSID={phpsessid}',
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                )
                resp.raise_for_status()
                return parse_flights(resp.text)
        except httpx.RequestError as exc:
            raise RuntimeError(f'eChronometraż fetch failed: {exc}') from exc
