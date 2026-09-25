# ROR API Architecture

This document describes the architecture of the [Research Organization Registry (ROR) API](https://ror.org) codebase. It is intended as context for coding agents and contributors working on this repository.

Public API documentation lives at https://ror.readme.io. Operational data workflows are managed in sibling repos: [ror-data](https://github.com/ror-community/ror-data) (full dumps), [ror-records](https://github.com/ror-community/ror-records) (incremental updates), and [ror-schema](https://github.com/ror-community/ror-schema) (JSON schema).

---

## Purpose

The ROR API provides:

1. **Public read API** — search, filter, retrieve, and affiliation-match research organizations stored in Elasticsearch.
2. **Internal write helpers** — generate schema-valid ROR record JSON (single record, bulk CSV) for the separate data-release pipeline. These endpoints do **not** write directly to the search index.
3. **Indexing operations** — management commands and authenticated HTTP endpoints to load organization data from GitHub releases or AWS S3 into Elasticsearch.

---

## High-Level Architecture

```
                    ┌─────────────────────────────────────────┐
                    │           Clients / Integrators          │
                    │  (ror-app UI, Crossref, publishers…)   │
                    └────────────────────┬────────────────────┘
                                         │ HTTPS
                                         ▼
                    ┌─────────────────────────────────────────┐
                    │   Nginx + Phusion Passenger (port 80)   │
                    │   WSGI entry: rorapi/wsgi.py            │
                    └────────────────────┬────────────────────┘
                                         │
                    ┌────────────────────▼────────────────────┐
                    │         Django 5.2 + DRF (rorapi/)        │
                    │  views → queries/matching/create_update   │
                    └───────┬──────────────────────┬───────────┘
                            │                      │
              ┌─────────────▼──────────┐   ┌───────▼────────────┐
              │  Elasticsearch 7       │   │  MySQL 8           │
              │  index: organizations-v2│   │  Client model only │
              └────────────────────────┘   └────────────────────┘
                            ▲
                            │ bulk index / reindex
              ┌─────────────┴──────────┐
              │  Management commands   │
              │  setup, indexror, …    │
              └─────────────┬──────────┘
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
   GitHub (ror-data)   AWS S3 (DATA_STORE)   Geonames (update_address)
```

**Key design choice:** Organization records live in **Elasticsearch**, not in Django ORM models. Django models under `rorapi/v2/models.py` are plain Python classes that wrap ES hit objects for serialization — except `Client`, which is a real Django model backed by MySQL.

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.12 |
| Web framework | Django 5.2.17 (LTS) |
| REST API | Django REST Framework 3.18.1 (URL path versioning, v2 only) |
| Search | Elasticsearch 7.10.1 via `elasticsearch` + `elasticsearch_dsl` 7.4.1 |
| Relational DB | MySQL 8 (client registration only) |
| App server | Phusion Passenger + Nginx (`vendor/docker/webapp.conf`) |
| Container | Docker (`Dockerfile` based on `phusion/passenger-python312:3.2.0`) |
| Observability | Sentry (`sentry-sdk` 1.45.1), django-prometheus 2.4.1 |
| Feature flags | LaunchDarkly (`rorapi/common/features.py`; `launchdarkly-server-sdk` 7.6.1) |
| Email | django-ses 4.8.0 (client ID registration emails) |
| External packages | `update_address` (Geonames enrichment), `jsonschema` 3.2.0, `rapidfuzz` 3.6.1, `boto3` (unpinned), `pandas` 2.2.3 |

Pins above match `[requirements.txt](requirements.txt)` on `dev` at the time of writing.

---

## Repository Layout

```
ror-api/
├── manage.py                 # Django entry point
├── requirements.txt
├── Dockerfile
├── docker-compose.yml        # Local: web + elasticsearch7 + mysql
├── rorapi/
│   ├── settings.py           # Central config, ES client, AWS, env vars
│   ├── wsgi.py
│   ├── common/               # Shared logic (most application code)
│   │   ├── urls.py           # All HTTP routes
│   │   ├── views.py          # ViewSets and APIViews
│   │   ├── queries.py        # Search/retrieve param validation + ES queries
│   │   ├── es_utils.py       # ESQueryBuilder
│   │   ├── matching.py       # Multi-search affiliation matching
│   │   ├── matching_single_search.py  # Single-search affiliation matching
│   │   ├── create_update.py  # Record JSON generation (POST/PUT)
│   │   ├── csv_bulk.py       # Bulk CSV processing
│   │   ├── csv_create.py     # CSV → new record
│   │   ├── csv_update.py     # CSV → updated record
│   │   ├── record_utils.py   # Schema validation, language codes
│   │   ├── serializers.py    # Shared serializers (Errors, buckets)
│   │   └── models.py         # Errors, Entity, aggregation buckets
│   ├── v2/                   # v2 schema-specific code
│   │   ├── models.py         # Organization, ListResult, MatchingResult, Client (ORM)
│   │   ├── serializers.py  # Response + Client registration serializers
│   │   ├── record_constants.py
│   │   ├── record_template.json
│   │   ├── ror_schema_v2_1.json  # Vendored JSON schema for write validation
│   │   └── index_template_es7.json  # ES index template + mappings
│   ├── management/commands/  # CLI indexing and legacy GRID tools
│   ├── migrations/           # Django migrations (Client model)
│   └── tests/                # Unit, integration, functional, affiliation suites
└── vendor/docker/            # Nginx, env, Terraform var templates for deploy
```

There is **no v1 API code path** in active use. `REST_FRAMEWORK['ALLOWED_VERSIONS']` is `['v2']` only.

---

## HTTP API Surface

Routes are defined in `rorapi/common/urls.py`. Version prefix `v2/` is optional for some legacy paths.

### Public read endpoints (GET, no auth)

| Route | Handler | Purpose |
|-------|---------|---------|
| `GET /v2/organizations` | `OrganizationViewSet.list` | Search, filter, or affiliation match |
| `GET /v2/organizations/{id}` | `OrganizationViewSet.retrieve` | Fetch one org by ROR ID (URL or bare ID) |
| `GET /heartbeat`, `GET /v2/heartbeat` | `HeartbeatView` | Health check (ES index exists) |
| `GET /validate-client-id/{client_id}/` | `ValidateClientView` | Check if Client-Id is registered |

### Authenticated write / admin endpoints (POST/PUT; `Token` + `Route-User` headers)

| Route | Handler | Purpose |
|-------|---------|---------|
| `POST /v2/organizations` | `OrganizationViewSet.create` | Generate new record JSON (does **not** index) |
| `PUT /v2/organizations/{id}` | `OrganizationViewSet.update` | Generate updated record JSON (does **not** index) |
| `POST /v2/bulkupdate` | `BulkUpdate` | CSV bulk create/update → zip on S3 |
| `POST /v2/indexdata/{branch}` | `IndexData` | Incremental index from S3 directory |
| `POST /v2/indexdatadump/{filename}/{test\|prod}` | `IndexDataDump` | Full reindex from GitHub data dump |
| `GET /generateid` | `GenerateId` | Generate unused ROR ID |
| `GET /v2/generateaddress/{geonamesid}` | `GenerateAddress` | Geonames location enrichment |

### Client registration (POST, no Token auth)

| Route | Handler | Purpose |
|-------|---------|---------|
| `POST /v2/register` | `ClientRegistrationView` | Register for rate-limit Client-Id; sends email via SES |

### Auth model

- **`OurTokenPermission`** (`views.py`): GET is always allowed. Mutating methods require `Token` and `Route-User` headers matching env vars `TOKEN` and `ROUTE_USER` (compared with `hmac.compare_digest` when both sides are present). Access is denied if either env var or either header is missing/empty.
- **`Client-Id` header**: Not authentication. Registered clients get higher rate limits (enforced outside this repo, typically at the edge). CORS allows the `Client-Id` header.

---

## Request Flow: Search & Retrieve

```
GET /v2/organizations?query=…&filter=…&page=…
        │
        ▼
OrganizationViewSet.list
        │
        ├─ affiliation param? ──► matching.py OR matching_single_search.py
        │                           (see Affiliation Matching below)
        │
        └─ else ──► queries.search_organizations(params)
                        │
                        ├─ validate(params)  # allowed keys, filters, page range
                        ├─ build_search_query(params)  # ESQueryBuilder
                        ├─ execute ES search on organizations-v2
                        └─ wrap hits → ListResultV2 → ListResultSerializerV2
```

```
GET /v2/organizations/{pk}
        │
        ▼
get_ror_id(pk) → retrieve_organization(ror_id) → OrganizationSerializerV2
```

**Search parameters** (validated in `queries.py`):

- `query` — free-text search against nested `names_ids` field
- `query.advanced` — Elasticsearch query_string syntax with field allowlist
- `filter` — comma-separated `field:value` filters (types, status, country, geonames fields, continent)
- `page` — pagination (page size = `ES_VARS['BATCH_SIZE']` = 20, max page = 500)
- `all_status` — include inactive records when not filtering by status

**Default behavior:** Active records only (`status:active` filter applied unless `all_status` or explicit status filter).

---

## Request Flow: Affiliation Matching

Triggered by `?affiliation=…` on `GET /v2/organizations`.

Two strategies exist:

| Strategy | Module | Selection |
|----------|--------|-----------|
| Multi-search (legacy default) | `common/matching.py` | Default unless `SINGLE_SEARCH_DEFAULT=True` or `single_search` param |
| Single-search (Marple-derived) | `common/matching_single_search.py` | `SINGLE_SEARCH_DEFAULT=True`, or `?single_search`, or when multisearch not requested |

Both:

1. Parse country hints from affiliation string using `countries.txt` + geonamescache
2. Query ES nested `affiliation_match.names` (indexed at ingest time)
3. Score candidates with fuzzy matching (`rapidfuzz`)
4. Return `MatchingResult` with chosen match, score, matching_type, substring

Response uses `MatchingResultSerializerV2`.

---

## Request Flow: Record Generation (Not Indexing)

**Important for agents:** `POST`/`PUT` on `/organizations` and `POST` on `/bulkupdate` produce **files for the ror-records release workflow**. They validate against the vendored schema at `rorapi/v2/ror_schema_v2_1.json` (loaded on first write via `get_v2_schema()` in `create_update.py`) and enrich Geonames data, but do **not** call Elasticsearch bulk index.

```
POST /v2/organizations  (JSON body)
        │
        ▼
new_record_from_json() in create_update.py
        ├─ add optional field defaults
        ├─ update_address.new_geonames_v2() per location
        ├─ generaterorid.check_ror_id() — collision-safe ID
        ├─ jsonschema validation (vendored v2.1 schema)
        └─ sort fields → OrganizationSerializerV2 response

PUT /v2/organizations/{id}
        │
        ▼
retrieve existing from ES → update_record_from_json()
```

Bulk CSV path: `BulkUpdate` → `validate_csv()` → `process_csv()` → per-row `new_record_from_csv` / `update_record_from_csv` → zip uploaded to S3 (`DATA_STORE` / `PUBLIC_STORE`).

---

## Elasticsearch Data Model

- **Index name:** `organizations-v2` (`ES_VARS['INDEX_V2']`)
- **Template:** `rorapi/v2/index_template_es7.json`
- **Document ID:** Organization `id` (full URL, e.g. `https://ror.org/01an7q238`)

Each indexed document is the ROR v2 JSON record plus **derived fields** added at index time (in `indexror.py` and `indexrordump.py`):

| Derived field | Purpose |
|---------------|---------|
| `names_ids` (nested) | Searchable names + external IDs for general query |
| `affiliation_match` (nested) | Optimized structure for affiliation matching |

Index creation: `python manage.py createindex`  
Deletion: `python manage.py deleteindex`

Local/docker ES uses basic auth `(elastic, ELASTIC_PASSWORD)`. Remote AWS OpenSearch uses `AWS4Auth`.

---

## Indexing Pipelines

### Full reindex from GitHub data dump

Used for local dev, CI test setup, and disaster recovery.

```
python manage.py setup {dump-filename} -s 2 [-t]
```

Orchestration (`setup.py`):

1. Verify dump exists in [ror-data](https://github.com/ror-community/ror-data) or [ror-data-test](https://github.com/ror-community/ror-data-test) via GitHub API (`GITHUB_TOKEN` required)
2. `getrordump` — download zip
3. `deleteindex` — drop existing index
4. `createindex` — apply template, create index
5. `indexrordump` — bulk load all records with derived fields

HTTP equivalent: `POST /v2/indexdatadump/{filename}/{test|prod}`

### Incremental index from S3

Used in production data deployment (triggered from [ror-records](https://github.com/ror-community/ror-records) GitHub Actions).

```
python manage.py indexror {s3-directory}
```

Or: `POST /v2/indexdata/{branch}`

Flow (`indexror.py`):

1. Download `{dir}/files.zip` from S3 bucket `DATA_STORE`
2. Extract JSON record files
3. **Backup current index** via reindex to `organizations-v2-tmp`
4. Bulk upsert changed records (with derived fields)
5. On `TransportError`, reindex backup back to restore; delete tmp index

Requires AWS credentials and `DATA_STORE` env var.

---

## Django / MySQL Usage

MySQL stores **only** the `Client` model (`rorapi/v2/models.py`):

- Registration fields: email, name, institution, country, ror_use
- System: `client_id` (32-char random), timestamps, request counters

Run migrations after DB is up:

```bash
python manage.py migrate
```

All other "models" (`Organization`, `ListResult`, etc.) are in-memory wrappers around Elasticsearch responses, not Django ORM entities.

---

## Configuration & Environment Variables

Loaded from environment and optional root `.env` file (`python-dotenv`).

| Variable | Purpose |
|----------|---------|
| `ELASTIC7_HOST`, `ELASTIC7_PORT`, `ELASTIC_PASSWORD` | Elasticsearch connection |
| `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT` | MySQL for Client model |
| `DATA_STORE`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | S3 indexing and bulk upload |
| `PUBLIC_STORE` | Public URL base for bulk update zip downloads |
| `GITHUB_TOKEN` | Fetch data dumps from GitHub |
| `ROUTE_USER`, `TOKEN` | Admin API authentication |
| `ROR_BASE_URL` | Base URL configuration |
| `SENTRY_DSN` | Error reporting |
| `LAUNCH_DARKLY_KEY` | Feature flags |
| `SINGLE_SEARCH_DEFAULT` | Default affiliation matcher (`True`/`False`) |
| `ENABLE_BEHAVIORAL_LIMITING` | Rate limiting toggle (edge behavior) |
| `SECRET_KEY` | Django secret (falls back to a hardcoded default if unset; `DEBUG` is always `False`) |
| `ALLOWED_HOSTS` | Currently hardcoded to `['*']` in settings |
| `AWS_REGION` | SES + AWS auth region |

See `README.md` for local Docker `.env` template.

---

## Local Development

```bash
docker-compose up -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py setup v1.0-2022-03-17-ror-data -s 2
# API at http://localhost:9292/v2/organizations
```

- Port **9292** maps to container port 80
- `./rorapi` is volume-mounted for live code edits
- Services: `web`, `elasticsearch7`, `db`

---

## Testing

| Suite | Path | CI status |
|-------|------|-----------|
| Unit | `rorapi.tests.tests_unit` | Runs in GitHub Actions |
| Integration | `rorapi.tests.tests_integration` | Commented out in CI (TODO) |
| Functional | `rorapi.tests.tests_functional` | Commented out in CI |
| Affiliation eval | `rorapi.tests.tests_affiliations` | Manual / local |

CI workflow (`.github/workflows/run_tests.yml`):

1. Spin up ES 7.10 + MySQL service containers
2. `pip install -r requirements.txt`
3. `python manage.py setup $TEST_DATA_DUMP_FILE -t` (test data from ror-data-test)
4. `python manage.py test rorapi.tests.tests_unit`

Run locally (with services up and data indexed):

```bash
docker-compose exec web python manage.py test rorapi.tests.tests_unit
docker-compose exec web python manage.py test rorapi.tests.tests_integration
docker-compose exec web python manage.py test rorapi.tests.tests_functional
```

---

## Deployment & CI/CD

| Branch / event | Workflow | Docker tag | Deploy target |
|----------------|----------|------------|---------------|
| Push to `dev` | `dev.yml` | `rorcommunity/ror-api:dev` | Terraform in [new-deployment](https://github.com/ror-community/new-deployment) |
| Push to `staging` | `staging.yml` | `:staging` | Same pattern |
| GitHub Release | `release.yml` | release tag | Production |
| Pull request | `pull-request.yml` | — | Tests only |

Deploy mechanism: GitHub Action updates `_ror-api-*.auto.tfvars` in the `new-deployment` repo (from templates in `vendor/docker/`), triggering Terraform infrastructure rollout. Images are pushed to Docker Hub (`rorcommunity/ror-api`).

---

## Legacy Code

Commands prefixed with `legacy*` (GRID conversion, old upgrade paths) are **non-functional** — referenced data was moved to ror-data. GRID-based generation ended March 2022. Do not extend or rely on these unless explicitly reviving historical tooling.

`settings.py` still contains commented GRID/ROR_DUMP version history for reference. `GRID_REMOVED_IDS` is an empty list retained for a check in `retrieve_organization`.

---

## External Dependencies & Related Repos

| Repo / service | Role |
|----------------|------|
| [ror-community/ror-data](https://github.com/ror-community/ror-data) | Production full data dumps (zip) |
| [ror-community/ror-data-test](https://github.com/ror-community/ror-data-test) | Test dumps for CI/local |
| [ror-community/ror-records](https://github.com/ror-community/ror-records) | Record PR workflow → S3 → `indexror` |
| [ror-community/ror-schema](https://github.com/ror-community/ror-schema) | Upstream JSON schema (vendored copy lives in-repo) |
| [ror-community/update_address](https://github.com/ror-community/update_address) | Geonames location enrichment |
| [ror-community/ror-app](https://github.com/ror-community/ror-app) | Public search UI (separate repo) |
| [ror-community/new-deployment](https://github.com/ror-community/new-deployment) | Terraform / infra |

---

## Agent Guidance: Common Tasks

### Add or change a search/filter parameter

1. Update allowlists in `rorapi/common/queries.py` (`ALLOWED_*` constants)
2. Extend `build_search_query()` and/or `validate()`
3. If ES mapping changes are needed, edit `rorapi/v2/index_template_es7.json` and plan a reindex
4. Add tests under `rorapi/tests/tests_unit/` or `tests_integration/`

### Change affiliation matching behavior

- Multi-search logic: `rorapi/common/matching.py`
- Single-search logic: `rorapi/common/matching_single_search.py`
- ES query shape: `ESQueryBuilder.add_affiliation_query()` in `es_utils.py`
- Indexed field shape: `get_affiliation_match_doc()` in `indexror.py` / `indexrordump.py`
- Default strategy: `SINGLE_SEARCH_DEFAULT` env var or request params in `OrganizationViewSet.list`

### Change record JSON generation / validation

- Core logic: `create_update.py`, `record_utils.py`, `v2/record_constants.py`
- Schema is the vendored `rorapi/v2/ror_schema_v2_1.json`, loaded lazily by `get_v2_schema()` on first write
- CSV paths: `csv_create.py`, `csv_update.py`, `csv_utils.py`, `csv_bulk.py`

### Add a new authenticated admin endpoint

1. Add view in `rorapi/common/views.py` with `OurTokenPermission`
2. Register route in `rorapi/common/urls.py`
3. Add unit tests in `tests_views_v2.py`

### Reindex after mapping changes

1. Update `index_template_es7.json`
2. Run full `setup` command (deletes and recreates index) — not incremental `indexror`
3. Verify with `GET /v2/heartbeat` and search tests

### What NOT to assume

- POST/PUT organizations **do not** update Elasticsearch; production updates go through ror-records → S3 → `indexror`
- v1 schema/index support has been removed
- Django ORM is not used for organization records
- Rate limiting for public API is largely enforced outside this application (Client-Id registration is stored here; enforcement is at infrastructure layer)

---

## Key Files Quick Reference

| Concern | Primary file(s) |
|---------|-----------------|
| Routes | `rorapi/common/urls.py` |
| HTTP handlers | `rorapi/common/views.py` |
| Search/retrieve | `rorapi/common/queries.py` |
| ES query building | `rorapi/common/es_utils.py` |
| Affiliation match | `matching.py`, `matching_single_search.py` |
| Record create/update | `create_update.py`, `csv_*.py` |
| Vendored JSON schema | `rorapi/v2/ror_schema_v2_1.json` |
| ES index template | `rorapi/v2/index_template_es7.json` |
| Settings / clients | `rorapi/settings.py` |
| Full reindex CLI | `management/commands/setup.py` |
| Incremental index CLI | `management/commands/indexror.py` |
| ROR ID generation | `management/commands/generaterorid.py` |
| Response serializers | `rorapi/v2/serializers.py` |
