# SCD Type 2 Customer Dimension Pipeline

## Overview

This project implements a Slowly Changing Dimension Type 2 (SCD2) data engineering pipeline using Python and SQLite. It preserves customer history, detects attribute changes, handles late-arriving events, validates input records, quarantines invalid data, and records pipeline execution metrics.

The solution is designed to run locally without cloud credentials or third-party Python dependencies.

## Architecture

```text
CSV Source
    |
    v
Schema and Record Validation
    |
    v
Duplicate Detection
    |
    +---- Invalid Records ----> Quarantine
    |
    v
Source Event Ledger
    |
    v
Effective-Time History Rebuild
    |
    v
SCD Type 2 Customer Dimension
    |
    v
Reconciliation and Run Metrics
```

## Technology Stack

- Python 3.10+
- SQLite
- CSV
- Python unittest
- Git and GitHub

## Project Structure

```text
scd2-data-pipeline/
├── src/
│   ├── __init__.py
│   ├── pipeline.py
│   ├── generate_data.py
│   └── reconcile.py
├── tests/
│   └── test_pipeline.py
├── data/
│   └── sample.csv
├── output/
├── docs/
│   └── data_dictionary.md
├── README.md
├── requirements.txt
└── .gitignore
```

## Setup

Requirements: Python 3.10 or newer and Windows PowerShell.

Create and activate a virtual environment:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

The project uses only Python's standard library, so installing third-party dependencies is unnecessary.

## Run the Pipeline

Run the automated tests:

```powershell
python -m unittest discover -s tests -v
```

Process the sample dataset:

```powershell
python -m src.pipeline --input data/sample.csv
```

The default SQLite database is created at `output/scd2.db`.

## Generate a Larger Dataset

Generate 100,000 reproducible synthetic records:

```powershell
python -m src.generate_data --count 100000 --seed 42 --output data/benchmark.csv
```

Run the pipeline against the generated dataset:

```powershell
python -m src.pipeline --input data/benchmark.csv --db output/benchmark.db
```

Run reconciliation checks:

```powershell
python -m src.reconcile
```

The reconciliation report is written to `output/reconciliation_report.json`.

## Source Schema

The input CSV must contain these columns in the specified order:

`customer_id,event_id,effective_at,name,email,city`

| Field | Description |
|---|---|
| `customer_id` | Stable customer business key |
| `event_id` | Unique source event identifier |
| `effective_at` | ISO-8601 timestamp with timezone |
| `name` | Customer name |
| `email` | Customer email |
| `city` | Customer city |

All fields are required. Timestamps are normalized to UTC. Missing values, invalid email formats, and conflicting event IDs are rejected. Unexpected CSV headers or column order fail the batch.

## SCD Type 2 Design

The pipeline maintains four SQLite tables:

- `source_events`: accepted source events and attribute hashes.
- `customer_dimension`: effective-dated customer history.
- `quarantine`: rejected records and their reasons.
- `pipeline_runs`: run IDs, execution status, row counts, duration, and errors.

### Effective dates

- `valid_from` is inclusive.
- `valid_to` is exclusive.
- `valid_to IS NULL` identifies the current version.
- `is_current = 1` identifies the current row.

### Change detection

A SHA-256 hash of tracked customer attributes identifies changes. When attributes change, a new historical version is created. No-op updates remain in the source ledger without creating unnecessary dimension versions.

### Late-arriving events

Events are processed in effective-time order. A late-arriving event causes the affected customer's timeline to be rebuilt, allowing historical intervals to be corrected.

### Same-timestamp events

When multiple events for one customer share the same effective timestamp, the lexicographically greatest `event_id` determines the dimension representation. All accepted events remain in the source ledger. This deterministic rule compensates for the absence of an authoritative source sequence number.

### Idempotency

Repeated accepted events are detected using their event IDs and content. Identical replays are skipped, while conflicting reuse of an event ID is rejected.

## Data Quality and Observability

The pipeline validates required fields, timestamp formats, email formats, unexpected fields, and duplicate event IDs.

Rejected records retain their source file, input row number, raw record, and rejection reason.

Each run records:

- Run ID and source file
- Start and end timestamps
- Input row count
- Newly inserted events
- Duplicate count
- Rejected count
- Resulting dimension row count
- Execution duration and failure reason

## Testing

The automated test suite covers:

- Valid input and late-arriving events
- Empty input
- Repeated events and idempotency
- Conflicting duplicate event IDs
- Missing fields and invalid email formats
- Timezone validation
- No-op updates
- Unexpected schema fields
- Same-timestamp events
- Current-row invariants

Run the tests using:

```powershell
python -m unittest discover -s tests -v
```

## Reconciliation

The reconciliation script checks for duplicate dimension versions, invalid effective intervals, customers without exactly one current row, and inconsistencies between current flags and effective end dates.

A successful report should show zero violations for all four checks.

## Performance

A recorded local benchmark processed 100,000 synthetic input records in approximately 8.43 seconds. Actual performance depends on hardware, event distribution, and database state.

A reasonable future optimization is incremental timeline repair rather than rebuilding the full history of every affected customer.

## Recovery and Limitations

Accepted source events and dimension changes are handled transactionally. After a failed run, the same input can be retried because identical accepted events are skipped.

This implementation is intended for local execution and moderate workloads. It is not a distributed processing platform. Same-timestamp ordering is inferred from event IDs, email validation is basic, and complete per-customer timeline rebuilding may become expensive for very long histories.

All supplied data is synthetic.

## Verification Summary

The recorded implementation run completed 12 automated tests successfully. A 100,000-event benchmark also completed, and the reconciliation report recorded zero violations across its four checks.

## AI Use Disclosure

AI assistance was used for implementation scaffolding, test-case design, debugging guidance, and documentation. The implementation and its outputs were executed and reviewed locally. The candidate is responsible for understanding the design choices, verifying the behavior, and explaining the limitations of the solution.
