# Data Dictionary

## source_events

| Column | Meaning |
|---|---|
| event_id | Unique accepted source event ID |
| customer_id | Customer business key |
| effective_at | Effective timestamp normalized to UTC |
| name | Customer name |
| email | Customer email |
| city | Customer city |
| payload_hash | Hash of tracked attributes |
| source_file | Source file or input label |
| ingested_at | Event ingestion timestamp |

## customer_dimension

| Column | Meaning |
|---|---|
| customer_sk | Deterministic dimension version key |
| customer_id | Customer business key |
| name | Historical customer name |
| email | Historical customer email |
| city | Historical customer city |
| attribute_hash | Change detection hash |
| valid_from | Inclusive version start |
| valid_to | Exclusive version end; NULL for current |
| is_current | 1 for current version, otherwise 0 |

## quarantine

| Column | Meaning |
|---|---|
| reject_id | Quarantine row identifier |
| run_id | Processing run identifier |
| source_file | Input source |
| row_number | Input record number |
| raw_record | Original record serialized as JSON |
| reason | Validation or duplicate conflict reason |
| rejected_at | Rejection timestamp |

## pipeline_runs

Tracks run ID, source file, start/end timestamps, status, input count, inserted
events, duplicates, rejects, dimension row count, duration, and failure reason.

## Grain and relationships

- source_events: one row per accepted event ID.
- customer_dimension: one row per customer version.
- quarantine: one row per rejected input occurrence.
- pipeline_runs: one row per pipeline attempt.

customer_id is the shared business key between the event ledger and dimension.
