# OSRS API Integration

Base URL:
https://prices.runescape.wiki/api/v1/osrs

Endpoints used by adapter design:

- /mapping
- /latest
- /5m
- /1h
- /timeseries?timestep={timestep}&id={item_id}

## Responsibilities

- Validate and parse external payloads via dedicated DTOs.
- Map DTOs to domain entities/value objects.
- Preserve source timestamp and ingestion timestamp separately.
- Surface partial failures and avoid all-or-nothing behavior.

## Configuration

- OSRS_WIKI_BASE_URL
- OSRS_WIKI_USER_AGENT
- HTTP_TIMEOUT_SECONDS
- HTTP_MAX_RETRIES
- HTTP_BACKOFF_BASE_SECONDS

## User-Agent policy

All requests must include a descriptive User-Agent. No real personal email is committed. Live collector should refuse to run if default placeholder is unchanged.

## Timeout policy

Use explicit connection and read timeouts through httpx.Timeout.

## Retry policy

Retry transient failures only:

- network errors
- HTTP 5xx
- HTTP 408
- HTTP 429

Do not retry other 4xx responses. Use bounded exponential backoff with jitter.

## Polling policy

Do not poll aggressively. Collector interval is configurable and defaults to 5 minutes.

## Payload validation

- Treat payload as untrusted.
- Ignore unknown fields by default where safe.
- Reject structurally invalid required fields.

## Idempotency

Persistence layer upserts observations by natural key (item, interval, source_timestamp).

## Caching strategy

Phase 0: no persistent cache. Optional in-memory request-scope caching may be introduced for repeated mapping fetches in a single run.

## Contract testing strategy

- Use frozen JSON fixtures for endpoint payloads.
- Parse fixtures through DTOs and mapper logic.
- Do not call live OSRS API in standard test suites.

## Data freshness semantics

Freshness is measured against source_timestamp, not only ingestion time.
