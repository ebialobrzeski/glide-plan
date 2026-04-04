# GlideLog — Plan projektu

## Cel

Portal webowy dla pilotów szybowcowych umożliwiający:
- Import danych z systemu eChronometraż (ab-pilot.echronometraz.pl)
- Przeglądanie dziennika lotów z filtrami i statystykami
- System alertów o ważności uprawnień i regularności lotów
- Panel admina do zarządzania użytkownikami
- Obsługa wielu pilotów (multi-user)

---

## Stack technologiczny

GlideLog implementowany jako moduł w istniejącym projekcie **GlidePlan** (`soaring_cup_web`).

| Warstwa | Technologia |
|---|---|
| Backend | Python 3.11 + **Flask 3.1** (istniejący) |
| Baza danych | PostgreSQL 16 (istniejący) |
| ORM + migracje | SQLAlchemy 2.0 + Alembic (istniejący) |
| Auth | bcrypt + session (istniejący system GlidePlan) |
| Szyfrowanie haseł connectorów | Fernet (reużywa SECRET_KEY z GlidePlan) |
| Scraping | httpx + BeautifulSoup4 |
| Frontend | Vanilla JS + Shoelace + Chart.js (istniejący stack GlidePlan) |
| Konteneryzacja | Docker Compose (istniejący) |

---

## Struktura projektu

GlideLog to nowy moduł w istniejącym repo `soaring_cup_web`. Zmiany minimalne — dokładamy foldery, nie ruszamy istniejącego kodu.

```
soaring_cup_web/                        # istniejące repo GlidePlan
├── app.py                              # istniejący — dodajemy rejestrację blueprintów
├── backend/
│   ├── routes/
│   │   ├── planner.py                  # istniejące
│   │   ├── waypoints.py                # istniejące
│   │   └── logbook/                    # NOWE — GlideLog
│   │       ├── __init__.py             # Blueprint 'logbook', prefix /logbook
│   │       ├── flights.py              # /logbook/flights
│   │       ├── connectors.py           # /logbook/connectors
│   │       ├── stats.py                # /logbook/stats
│   │       ├── alerts.py               # /logbook/alerts
│   │       ├── import_.py              # /logbook/import
│   │       └── admin.py                # /logbook/admin
│   ├── services/
│   │   ├── ai_planner/                 # istniejące
│   │   └── connectors/                 # NOWE
│   │       ├── __init__.py             # fabryka get_connector()
│   │       ├── base.py                 # BaseConnector interface
│   │       ├── echrono.py              # EchronoConnector
│   │       ├── leonardo.py             # LeonardoConnector
│   │       ├── weglide.py              # WeGlideConnector
│   │       └── seeyou.py               # SeeYouConnector
│   └── models/
│       ├── waypoint.py                 # istniejące
│       ├── task.py                     # istniejące
│       ├── flight.py                   # NOWE
│       ├── connector.py                # NOWE
│       ├── import_log.py               # NOWE
├── templates/
│   ├── planner/                        # istniejące
│   └── logbook/                        # NOWE
│       ├── dashboard.html
│       ├── flights.html
│       ├── stats.html
│       ├── alerts.html
│       ├── import.html
│       └── connectors.html
├── static/
│   ├── js/                             # istniejące
│   └── logbook/                        # NOWE — Chart.js init, alpine components
├── alembic/                            # NOWE — migracje dla nowych tabel
├── docker-compose.yaml                 # istniejące — bez zmian
└── .env.example                        # istniejące — dodajemy nowe zmienne
```

---

## Schemat bazy danych

### Tabela `users`
Tabela `users` już istnieje w GlidePlan — rozszerzamy ją o kolumny GlideLog przez migrację Alembic.

```
-- istniejące kolumny GlidePlan (nie ruszamy):
id                          SERIAL / UUID, PK
username                    VARCHAR, UNIQUE, NOT NULL
email                       VARCHAR, UNIQUE, NOT NULL
password_hash               VARCHAR, NOT NULL           -- bcrypt (istniejące)
is_admin                    BOOLEAN                     -- istniejące
created_at                  TIMESTAMP                   -- istniejące
tier                        VARCHAR                     -- free/premium/admin (istniejące)

-- NOWE kolumny dodawane migracją Alembic:
logbook_enabled             BOOLEAN, DEFAULT true       -- każdy zarejestrowany użytkownik ma dostęp do GlideLog
logbook_medical_expiry      DATE, NULLABLE              -- data ważności orzeczenia lekarskiego
logbook_license_date        DATE, NULLABLE              -- data uzyskania licencji SPL
logbook_launch_methods      VARCHAR[], NULLABLE         -- metody startu z egzaminu ['W','S','TMG']
```

### Tabela `flights`
```
id              UUID, PK
external_id     VARCHAR, UNIQUE, NOT NULL   -- z flightShow&id=XXXXX (globalnie unikalny w eChronometraż)
user_id         UUID, FK users
date            DATE
aircraft_type   VARCHAR                     -- SZD-50-3, SZD-51-1 etc.
aircraft_reg    VARCHAR                     -- SP-3788 etc.
pilot           VARCHAR
instructor      VARCHAR, NULLABLE
task            VARCHAR                     -- SPL/I-1, TMG/1 etc.
launch_type     VARCHAR                     -- W (wyciągarka), S (samolot), inne
takeoff_airport VARCHAR
takeoff_time    TIME
landing_airport VARCHAR
landing_time    TIME
flight_time_min INTEGER                     -- czas lotu w minutach
landings        INTEGER
is_instructor   BOOLEAN
price           NUMERIC(10,2)
raw_data        JSONB                       -- wszystkie dane z parsera
source          VARCHAR  DEFAULT 'echrono'  -- echrono / manual / import
connector_id    UUID, FK connectors, NULLABLE
import_id       UUID, FK import_log, NULLABLE
synced_at       TIMESTAMP
```

### Tabela `sync_log`
```
id          UUID, PK
user_id     UUID, FK users
started_at  TIMESTAMP
finished_at TIMESTAMP, NULLABLE
status      VARCHAR                         -- running / success / error
message     TEXT, NULLABLE
flights_imported  INTEGER, DEFAULT 0
```


### Tabela `import_log`
```
id              UUID, PK
user_id         UUID, FK users
source_type     VARCHAR              -- leonardo / seeyou / weglide / excel / igc / manual
filename        VARCHAR, NULLABLE
imported_at     TIMESTAMP
flights_new     INTEGER, DEFAULT 0
flights_dup     INTEGER, DEFAULT 0
flights_error   INTEGER, DEFAULT 0
status          VARCHAR              -- success / partial / error
message         TEXT, NULLABLE
```


### Tabela `connectors`
```
id              UUID, PK
user_id         UUID, FK users
type            VARCHAR              -- echrono / leonardo / weglide / seeyou / manual
display_name    VARCHAR              -- np. "Aeroklub Białostocki"
base_url        VARCHAR, NULLABLE    -- np. https://ab-pilot.echronometraz.pl
login_encrypted VARCHAR, NULLABLE    -- Fernet(SECRET_KEY)
password_encrypted VARCHAR, NULLABLE -- Fernet(SECRET_KEY)
config          JSONB, NULLABLE      -- dodatkowe parametry specyficzne dla źródła
is_active       BOOLEAN, DEFAULT true
last_sync_at    TIMESTAMP, NULLABLE
last_sync_status VARCHAR, NULLABLE   -- success / error
created_at      TIMESTAMP
```

Przykłady pola `config` per typ:
```json
// echrono
{ "date_from": "2000-01-01", "filter_aircraft": null }

// leonardo
{ "api_key": "...", "pilot_id": "..." }

// weglide
{ "pilot_id": 12345, "include_club_flights": true }

// seeyou
{ "api_token": "...", "club_id": null }
```

---

## Deduplicacja lotów

- `external_id` pochodzi z atrybutu `href="...flightShow&id=XXXXX"` w HTML tabeli lotów
- Jest globalnie unikalny w systemie eChronometraż — nie ma potrzeby scopowania per user
- Constraint: `UNIQUE (external_id)` na tabeli `flights`
- Przy imporcie: `INSERT ... ON CONFLICT (external_id) DO NOTHING`

---

## Raw data — struktura JSONB

Każdy lot zapisuje w `raw_data` wszystkie dostępne dane:

```json
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
```

---

## API Endpointy

### Auth
```
POST /api/auth/register     -- rejestracja z tokenem zaproszenia
POST /api/auth/login        -- login → access token + refresh token
POST /api/auth/refresh      -- odśwież access token
POST /api/auth/logout
GET  /api/auth/me           -- dane zalogowanego użytkownika
```

### Ustawienia
```
PUT  /logbook/settings/echrono  -- zapisz login/hasło do eChronometraż (shortcut dla domyślnego connectora)
GET  /logbook/settings/echrono  -- pobierz (bez hasła)
```
> Uwaga: settings/echrono to tylko backwards-compatible shortcut. Docelowo wszystko przez /api/connectors.

### Synchronizacja
```
POST /logbook/sync              -- triggeruj sync (background task)
GET  /api/sync/status       -- status ostatniej synchronizacji
GET  /api/sync/history      -- historia synców
```

### Loty
```
GET /logbook/flights            -- lista z filtrami
  ?date_from=2025-01-01
  ?date_to=2025-12-31
  ?aircraft_type=SZD-50-3
  ?launch_type=W
  ?task=SPL
  ?page=1&limit=50

GET /logbook/flights/{id}       -- szczegóły lotu
```

### Statystyki
```
GET /logbook/stats/summary          -- łączny nalot, starty, koszty
GET /logbook/stats/by-month         -- nalot per miesiąc (wykres)
GET /logbook/stats/by-aircraft      -- nalot per typ/rejestracja
GET /logbook/stats/by-launch-type   -- wyciągarka vs aerohol
GET /logbook/stats/by-task          -- podział wg zadań
```

### Alerty
```
GET /logbook/alerts             -- lista aktywnych alertów dla zalogowanego pilota
```



### Connectors
```
GET    /logbook/connectors              -- lista connectorów użytkownika
POST   /logbook/connectors              -- dodaj nowy connector
PUT    /logbook/connectors/{id}         -- aktualizuj (login/hasło/config)
DELETE /logbook/connectors/{id}         -- usuń connector + powiązane loty?
POST   /logbook/connectors/{id}/sync    -- triggeruj sync dla konkretnego connectora
GET    /logbook/connectors/{id}/status  -- status ostatniej synchronizacji
POST   /logbook/connectors/{id}/test    -- test połączenia (czy login działa)
```

### Import i ręczny wpis
```
POST /logbook/import/upload     -- upload pliku (multipart/form-data)
POST /logbook/import/preview    -- parsuj plik → podgląd (nowe / duplikaty / błędy)
POST /logbook/import/confirm    -- zatwierdź import po podglądzie
GET  /logbook/import/history    -- historia importów użytkownika

POST   /logbook/flights/manual  -- ręczny wpis pojedynczego lotu
PUT    /logbook/flights/{id}    -- edycja lotu (tylko source=manual)
DELETE /logbook/flights/{id}    -- usuń lot (tylko source=manual)
```

### Admin
```
GET    /logbook/admin/users             -- lista użytkowników
PATCH  /logbook/admin/users/{id}        -- aktywuj/dezaktywuj
DELETE /logbook/admin/users/{id}        -- usuń użytkownika
GET    /logbook/admin/stats             -- statystyki wszystkich pilotów
```

---

## System alertów

| Alert | Warunek | Poziom |
|---|---|---|
| Brak startu z wyciągarki | > 30 dni | warning |
| Brak startu z wyciągarki | > 90 dni | danger |
| Brak startu aeroholem | > 90 dni | warning |
| Brak startu aeroholem | > 180 dni | danger |
| Brak lotu na danym typie statku | > 180 dni | info |
| Brak lotu ogółem | > 60 dni | warning |

- Progi konfigurowalne przez admina w panelu
- Alerty widoczne na dashboardzie pilota
- Admin widzi alerty wszystkich pilotów

---

## Scraper — logika

### Logowanie
```
POST https://ab-pilot.echronometraz.pl/index.php
Content-Type: application/x-www-form-urlencoded

login=XXXX&password=XXXX
```
- Odpowiedź: 302 redirect + Set-Cookie: PHPSESSID=XXXX
- Zapisujemy cookie do kolejnych requestów

### Pobieranie lotów
```
POST https://ab-pilot.echronometraz.pl/index.php?action=personel&start=loty
Cookie: PHPSESSID=XXXX
Content-Type: application/x-www-form-urlencoded

filters[perChrList][dateOd]=2000-01-01&filters[perChrList][dateDo]=2026-12-31
```
- Pierwsza synchronizacja: date_from=2000-01-01
- Kolejne synce: date_from = data ostatniego sukcesu

### Parser — skąd wyciągamy dane
- Tabela `<table class="table">` → wiersze `<tr>`
- `external_id` → atrybut `href` w pierwszym `<td>` (link do `flightShow&id=XXXXX`)
- Dane lotu → kolejne `<td>` w wierszu
- Dane ceny/załogi → atrybut `title` na `<tr>` (HTML z podziałem kosztów)

---

## Frontend — widoki

1. **Login** — formularz logowania do portalu
2. **Rejestracja** — formularz z polem na token zaproszenia
3. **Dashboard**
   - KPI: łączny nalot, liczba lotów, suma kosztów, ostatni lot
   - Wykres nalotu po miesiącach (Chart.js — bar chart)
   - Wykres podziału na typy statków (pie chart)
   - Panel alertów
4. **Tabela lotów**
   - Filtry: data od/do, typ statku, rodzaj startu, zadanie
   - Sortowanie po każdej kolumnie
   - Paginacja
5. **Import / Dodaj lot** (3 zakładki)
   - Zakładka "Import z pliku" — wybór źródła (Leonardo, SeeYou, WeGlide, Excel, IGC), drag & drop, podgląd z podziałem nowe/duplikaty/błędy, potwierdzenie
   - Zakładka "Ręczny wpis" — formularz z walidacją, pola: data, lotniska, czasy, statek, rejestracja, rola, metoda startu, zadanie, uwagi
   - Zakładka "Historia importów" — tabela z datą, źródłem, liczbą zaimportowanych/duplikatów, statusem
6. **Ustawienia**
   - Dane eChronometraż (login, hasło, URL)
   - Przycisk: "Synchronizuj teraz"
   - Status ostatniej synchronizacji
6. **Panel admina** (tylko is_admin=true)
   - Lista użytkowników + aktywacja/dezaktywacja
   - Generowanie linków zaproszeń
   - Statystyki wszystkich pilotów

---

## Docker Compose

GlidePlan ma już działający `docker-compose.yaml` — nie zmieniamy struktury, tylko dodajemy zmienne env w `.env`.

```yaml
# Istniejący docker-compose.yaml GlidePlan — bez zmian struktury.
# Dodaj tylko do sekcji environment lub .env nowe zmienne GlideLog (patrz sekcja env poniżej).
```

Frontend serwowany przez Flask jako szablony Jinja2 — tak samo jak reszta GlidePlan.

---

## Zmienne środowiskowe (.env.example)

GlidePlan ma już `.env.example` z PostgreSQL, SECRET_KEY itp. Dodajemy tylko nowe zmienne GlideLog:

```env
# --- istniejące zmienne GlidePlan (już są w .env) ---
# DATABASE_URL=...
# SECRET_KEY=...
# itd.

# --- NOWE zmienne dla GlideLog ---

# AES-256 — szyfrowanie haseł do eChronometraż i innych connectorów

# Email (Resend - https://resend.com) — już istnieje w GlidePlan
# RESEND_API_KEY — już skonfigurowany w .env GlidePlan, nie dodawaj ponownie
EMAIL_FROM=noreply@glideplan.org    # jeśli jeszcze nie ma
```

---


## Background sync — APScheduler

GlidePlan nie ma schedulera — dodajemy `APScheduler` jako jedyną nową zależność w `requirements.txt`:

```
APScheduler>=3.10
```

### Jak działa

```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

@scheduler.scheduled_job('interval', hours=24)
def sync_all_users():
    """Co 6 godzin synchronizuj wszystkich aktywnych użytkowników z ich connectorami."""
    users = db.session.query(User).filter_by(logbook_enabled=True).all()
    for user in users:
        for connector in user.connectors:
            if connector.is_active:
                sync_connector(connector)

scheduler.start()  # wywołaj przy starcie aplikacji w app.py
```

### Strategia sync

| Connector | Częstotliwość |
|---|---|
| eChronometraż | co 24h |
| Leonardo | co 24h |
| WeGlide | co 24h |
| SeeYou | co 24h |

### Ważne zasady

- Scheduler startuje razem z aplikacją Flask — w `app.py` po `app = Flask(__name__)`
- **Gunicorn gotcha — scheduler musi startować tylko raz.** Gunicorn domyślnie forkuje wiele worker procesów — każdy odpali `scheduler.start()` osobno, co skutkuje N równoległymi jobami. Rozwiązanie: zawsze używaj `coalesce=True` i `max_instances=1`, oraz startuj scheduler tylko w procesie głównym:
  ```python
  scheduler = BackgroundScheduler(
      job_defaults={'coalesce': True, 'max_instances': 1}
  )

  # Startuj tylko raz — nie w każdym forku Gunicorn
  import os
  if os.environ.get('WERKZEUG_RUN_MAIN') != 'false':
      scheduler.start()
  ```
  Alternatywnie w `gunicorn.conf.py` ustaw `preload_app = True` — wtedy scheduler startuje przed forkiem workerów i jest współdzielony
- Każdy sync zapisuje wynik do `sync_log` — sukces lub błąd z komunikatem
- Użytkownik może zawsze triggerować sync ręcznie przez `POST /logbook/connectors/{id}/sync` niezależnie od harmonogramu
- Nie blokuj głównego wątku — `BackgroundScheduler` działa w osobnym wątku automatycznie

## Kolejność implementacji

1. **Modele DB + Alembic** — fundament, najpierw
2. **Scraper + Parser** — przetestować na prawdziwych danych
3. **Auth** — reużywamy GlidePlan w całości, brak pracy
4. **API endpointy** — flights, stats, alerts, admin
5. **Frontend** — single HTML file
6. **Docker Compose** — deployment na NAS

---

## Instrukcje dla Claude Code

Czytasz ten dokument jako punkt startowy projektu. Poniżej szczegółowe wskazówki do każdego etapu.

### Krok 1 — Modele DB + Alembic

GlidePlan już używa SQLAlchemy 2.0 i PostgreSQL — dodajemy nowe modele do istniejącej struktury.

- Nowe modele umieść w `backend/models/` obok istniejących (`waypoint.py`, `task.py`)
- Sprawdź jak istniejące modele definiują `Base` — użyj tej samej instancji `DeclarativeBase`, nie twórz nowej
- Sprawdź czy Alembic jest już skonfigurowany w projekcie (`alembic/` lub `alembic.ini`) — jeśli tak, tylko dodaj nową migrację: `alembic revision --autogenerate -m "add_glidelog_tables"`
- Jeśli Alembic nie istnieje: `alembic init alembic`, ustaw `target_metadata` w `alembic/env.py` na ten sam `Base.metadata` co reszta modeli
- Kolumna `raw_data` — typ `JSONB`: `from sqlalchemy.dialects.postgresql import JSONB`
- UUID jako PK: `import uuid` i `default=uuid.uuid4`
- Tabela `users` już istnieje — dodaj nowe kolumny przez `op.add_column()` w migracji, nie redefiniuj całej tabeli
- Po migracji zweryfikuj: `alembic current` i `alembic history`


### Krok 1b — Architektura connectorów

Connectors to wzorzec Strategy Pattern — każdy typ źródła implementuje ten sam interfejs:

```python
class BaseConnector:
    async def test_connection(self) -> bool: ...
    async def fetch_flights(self, date_from: date, date_to: date) -> list[dict]: ...
    async def get_display_name(self) -> str: ...

class EchronoConnector(BaseConnector): ...
class LeonardoConnector(BaseConnector): ...
class WeGlideConnector(BaseConnector): ...
class SeeYouConnector(BaseConnector): ...
```

- Umieść w `app/services/connectors/` — każdy typ w osobnym pliku
- `app/services/connectors/__init__.py` eksportuje `get_connector(db_record) -> BaseConnector`
- Fabryka wybiera klasę na podstawie `connector.type`
- Przy syncu iteruj po wszystkich aktywnych connectorach użytkownika i wywołuj `fetch_flights()`
- Każdy lot zapisuj z `connector_id` — wiemy skąd pochodzi
- Przy konflikcie `external_id`: jeśli pochodzi z różnych connectorów → dopuść (różne systemy mogą mieć ten sam ID), jeśli z tego samego → pomiń (duplikat)

**Unikalne klucze deduplicacji per connector:**
```python
# eChronometraż: zewnętrzny ID z URL
unique_key = f"echrono:{external_id}"

# Leonardo, WeGlide, SeeYou: composite
unique_key = f"{connector.type}:{date}:{aircraft_reg}:{takeoff_time}"

# Ręczny wpis: UUID generowany przy zapisie
unique_key = f"manual:{uuid4()}"
```

Pole `raw_data.unique_key` — zapisuj ten klucz, sprawdzaj przed insertem.

**Migracja z obecnego modelu (echrono login w users):**
- Przy starcie aplikacji: jeśli `user.echrono_login` istnieje, auto-utwórz connector typu `echrono` dla tego użytkownika
- Po migracji: `user.echrono_login` i `user.echrono_password_encrypted` można zignorować (zostaw dla backwards compat)

### Krok 2 — Scraper + Parser

- Użyj `httpx` z `follow_redirects=False` przy logowaniu — chcemy złapać cookie z odpowiedzi 302, nie podążać za redirectem
- Po logowaniu wyciągnij `PHPSESSID` z `response.cookies`
- Przy pobieraniu lotów wyślij `dateOd=2000-01-01` i `dateDo=DZISIAJ` dla pierwszej synchronizacji
- Parser powinien działać na surowym HTML — napisz funkcję `parse_flights(html: str) -> list[dict]`
- Każdy wiersz `<tr>` w tabeli lotów ma atrybut `title` z HTML zawierającym szczegóły ceny i załogi — parsuj go osobno przez `BeautifulSoup`
- `external_id` wyciągaj z `href` w pierwszym `<td>` wiersza: regex `flightShow&id=(\d+)`
- Napisz testy jednostkowe dla parsera używając zapisanego HTML jako fixture — nie rób requestów sieciowych w testach
- Zapisz przykładowy HTML (kilka wierszy tabeli) jako `tests/fixtures/flights_sample.html`

### Krok 3 — Auth

Auth w GlidePlan już działa — **nie implementujemy od nowa**. Tylko podpinamy GlideLog pod istniejący system.

- Sprawdź jak GlidePlan chroni routy (`@login_required` decorator lub własny mechanizm) — użyj tego samego we wszystkich blueprintach `/logbook/`
- Sprawdź jak GlidePlan trzyma sesję użytkownika (`flask_login`, `session`, własne JWT) — użyj tej samej metody do pobierania `current_user`
- Hasła do eChronometraż szyfruj przez `cryptography` (Fernet) — użyj istniejącego `SECRET_KEY` z GlidePlan jako klucza: `Fernet(base64.urlsafe_b64encode(SECRET_KEY[:32].encode()))`
- Rejestracja i weryfikacja email już działają w GlidePlan — GlideLog reużywa tego bez żadnych zmian
- Email wysyłaj przez `resend` — biblioteka i `RESEND_API_KEY` już są w GlidePlan, sprawdź jak inne miejsca w kodzie wywołują Resend i użyj tego samego wzorca

### Krok 4 — API endpointy

- Używaj `APIRouter` z prefixami, np. `router = APIRouter(prefix="/api/flights", tags=["flights"])`
- Sync ręczny (`POST /logbook/connectors/{id}/sync`) — uruchamia sync w osobnym wątku (`threading.Thread`) i natychmiast zwraca `{"message": "sync started"}` — nie blokuj requesta
- Automatyczny sync działa przez APScheduler (patrz sekcja "Background sync")
- Status synca pobieraj z tabeli `sync_log` — ostatni rekord dla danego `user_id`
- Endpoint `GET /logbook/flights` — użyj SQLAlchemy query z dynamicznymi filtrami, dodaj paginację (`skip`, `limit`)
- Statystyki licz bezpośrednio w SQL/SQLAlchemy — nie ładuj wszystkich lotów do Pythona
- Alerty: serwis `alerts.py` powinien zwracać listę obiektów `{"type": "warning", "message": "...", "days_since": X}`


### Krok 4b — Import i ręczny wpis

**Pole `source` w tabeli `flights`:**
- `echrono` — synchronizacja z eChronometraż (domyślne)
- `manual` — ręczny wpis przez formularz
- `import` — import z pliku zewnętrznego

**Reguły nadpisywania:**
- Loty z `source=echrono` mogą być aktualizowane przez sync (ON CONFLICT DO UPDATE)
- Loty z `source=manual` lub `source=import` — sync ich **nigdy nie nadpisuje** (ON CONFLICT DO NOTHING)
- Usuwanie dozwolone tylko dla `source=manual` i `source=import`

**Flow importu z pliku (3 kroki):**
1. `POST /logbook/import/upload` → zapisz plik tymczasowo, zwróć `upload_id`
2. `POST /logbook/import/preview` → parsuj plik, sprawdź duplikaty przez `external_id` lub composite key `(date + aircraft_reg + takeoff_time)`, zwróć JSON z podziałem na `new / duplicate / error`
3. `POST /logbook/import/confirm` → zapisz tylko rekordy oznaczone `new`, utwórz rekord w `import_log`

**Obsługiwane formaty i parsery:**

| Format | Biblioteka Python | Uwagi |
|---|---|---|
| CSV ogólny | `pandas` lub `csv` | Auto-detect separatora |
| XLSX | `openpyxl` | Pierwszy arkusz |
| IGC | własny parser | Header: `HFDTE` (data), `B` records (czas/pozycja) |
| Leonardo CSV | `csv` | Kolumny: Date, Aircraft, Takeoff, Landing, Duration... |
| WeGlide CSV | `csv` | Kolumny: date, glider, launch\_time, landing\_time... |

**Parser IGC — kluczowe pola:**
```python
# Z nagłówka IGC
# HFDTE: data lotu (DDMMYY)
# HFGTYGLIDERTYPE: typ szybowca
# HFGIDGLIDERID: rejestracja

# Z rekordów B (fix co ~1s):
# B HHMMSS DDMMmmmN DDDMMmmmE V PPPPP GGGGG
# pierwsze B = czas startu, ostatnie B = czas lądowania
```

**Deduplicacja przy imporcie zewnętrznym:**
- Brak `external_id` (tylko eChronometraż go ma)
- Użyj composite key: `hash(user_id + date + aircraft_reg + takeoff_time)`
- Zapisz hash w polu `raw_data.import_hash`
- Przy kolejnym imporcie sprawdzaj po tym hashu

**Ręczny wpis — walidacja formularza:**
- `date` — wymagane, nie może być w przyszłości
- `takeoff_time` < `landing_time` — jeśli data ta sama
- `aircraft_reg` — format SP-XXXX (regex: `^SP-[A-Z0-9]{4}$`) lub inne formaty europejskie
- `flight_time_min` — obliczaj automatycznie z takeoff/landing, pozwól też na ręczny wpis
- `launch_type` — wymagane (W/S/E/TMG)
- `pilot_role` — wymagane (PIC/dual/supervised)

### Krok 5 — Frontend

GlidePlan używa **Vanilla JS + Shoelace + Leaflet** — dokładamy Chart.js i nowe szablony Jinja2.

- Nowe szablony umieść w `templates/logbook/` — wzoruj się na istniejących szablonach GlidePlan (layout, navbar, styl)
- Sprawdź istniejący base template (`templates/base.html` lub podobny) — nowe strony GlideLog dziedziczą z tego samego base
- Shoelace jest już załadowany — używaj komponentów `<sl-card>`, `<sl-button>`, `<sl-badge>` zamiast własnych
- Dodaj Chart.js do base template lub tylko do szablonów logbook: `<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>`
- Nowe pliki JS umieść w `static/logbook/` — np. `static/logbook/charts.js`, `static/logbook/alerts.js`
- Sesja użytkownika przez Flask session — nie potrzebujesz JWT ani interceptorów, Flask to obsługuje
- Wykresy inicjalizuj w `DOMContentLoaded` — dane przekazuj przez `data-*` atrybuty lub inline JSON w szablonie Jinja2:
  ```html
  <canvas id="monthlyChart" data-values="{{ monthly_data | tojson }}"></canvas>
  ```
- Filtry tabeli lotów — prosty fetch do `/logbook/flights?date_from=...` i re-render tabeli przez innerHTML

### Krok 6 — Docker Compose

GlidePlan ma już działający `docker-compose.yaml` — **nie tworzymy nowego**, tylko dodajemy zmienne środowiskowe.

- Otwórz istniejący `docker-compose.yaml` i `.env.example` — dodaj tylko nowe zmienne dla GlideLog (patrz sekcja env poniżej)
- Sprawdź czy `Dockerfile` używa `requirements.txt` — dodaj nowe zależności GlideLog (`httpx`, `beautifulsoup4`, `cryptography`, `openpyxl` (resend już jest w GlidePlan))
- Docker Compose już ma PostgreSQL 16, healthcheck i volumes — nic nie zmieniaj
- NAS (Ugreen ARM64) — istniejące obrazy już działają na ARM64, nowe zależności pip też są kompatybilne
- Po dodaniu nowych zmiennych env: `docker-compose up -d --build` żeby przebudować image

### Ogólne zasady

- Nigdy nie commituj `.env` — tylko `.env.example` z placeholder values
- GlidePlan używa własnego systemu config — sprawdź jak ładuje zmienne env (`os.getenv`, `python-dotenv`, `pydantic-settings`) i użyj tej samej metody
- Loguj błędy scrapera do tabeli `sync_log` z czytelnym komunikatem — użytkownik musi wiedzieć co poszło nie tak
- Odpowiedzi błędów — wzoruj się na istniejących endpointach GlidePlan (czy zwracają JSON `{"error": "..."}` czy Flask `abort()`)
- Przy błędzie logowania do eChronometraż (np. złe hasło) — nie crashuj, zapisz błąd do sync_log i zwróć czytelny komunikat
- Przed pisaniem kodu przejrzyj `app.py` i `backend/routes/` GlidePlan żeby zrozumieć istniejące wzorce — trzymaj się tych samych konwencji

---

## Notatki techniczne

- eChronometraż używa PHP sessions (PHPSESSID cookie)
- HTML response zawiera dane w tooltipach (`title` atrybut na `<tr>`) — tam są szczegóły cen i załogi
- `external_id` z `flightShow&id=XXXXX` jest globalnie unikalny w systemie
- Pierwsza synchronizacja pobiera wszystko od 2000-01-01 do dziś
- Kolejne synce są inkrementalne od daty ostatniego sukcesu
- URL systemu: `https://ab-pilot.echronometraz.pl/index.php`
- Login POST fields: `login` i `password`
- Loty POST: `index.php?action=personel&start=loty` z polami `filters[perChrList][dateOd]` i `filters[perChrList][dateDo]`
