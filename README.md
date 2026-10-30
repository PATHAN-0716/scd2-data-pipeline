# SCD Type 2 Customer Data Pipeline

### A Python and SQLite implementation for maintaining accurate customer history

---

## 1. Project Overview

Customer information changes over time. A customer may move to another city, update their email address, or change their name. In a traditional database, updating an existing record directly can result in losing the previous information.

This project addresses that problem using **Slowly Changing Dimension Type 2 (SCD Type 2)**.

Instead of overwriting customer records, the pipeline maintains historical versions. Whenever a tracked customer attribute changes, the previous version is closed and a new version is inserted. This makes it possible to understand both the customer's current information and how that information changed over time.

The solution is implemented using Python and SQLite, with a focus on data correctness, historical accuracy, repeatable processing, and automated validation.

---

## 2. Project Objectives

The main objectives of this project are:

- Implement SCD Type 2 logic for maintaining customer history.
- Process customer change events from CSV files.
- Detect changes in customer attributes using record hashing.
- Handle duplicate and conflicting source events.
- Support late-arriving events and chronological history reconstruction.
- Validate incoming data and quarantine invalid records.
- Maintain database consistency and idempotent processing.
- Test the implementation using automated test cases.
- Verify the final customer dimension through reconciliation checks.

---

## 3. Key Features

| Feature | Description |
|---|---|
| SCD Type 2 | Maintains historical versions instead of overwriting customer records. |
| Change Detection | Uses record hashes to identify changes in customer attributes. |
| Event Deduplication | Identifies duplicate events using unique event IDs. |
| Conflict Handling | Rejects reuse of an event ID with different data. |
| Idempotency | Reprocessing the same events does not create unnecessary versions. |
| Late-Arriving Events | Reconstructs the affected customer's history using effective timestamps. |
| Timestamp Validation | Parses timezone-aware timestamps and normalizes them to UTC. |
| Data Validation | Checks required fields and basic email validity. |
| Quarantine Handling | Stores invalid records separately with validation reasons. |
| Automated Testing | Covers important pipeline scenarios using Python `unittest`. |
| Reconciliation | Checks dimension integrity and generates a JSON report. |

---

## 4. Technology Stack

| Technology | Purpose |
|---|---|
| Python | Pipeline implementation and data processing |
| SQLite | Persistent storage for events and customer history |
| CSV | Input data format |
| `hashlib` | Record hash generation |
| `datetime` | Timestamp parsing and handling |
| `json` | Reconciliation report generation |
| `unittest` | Automated testing |
| Git | Version control |

The project uses Python standard-library modules and does not require third-party packages.

---

## 5. System Architecture

The pipeline follows a simple data processing flow:

```text
                  Customer CSV Input
                          |
                          v
                   CSV Ingestion
                          |
                          v
                Schema and Data Validation
                          |
                   +------+------+
                   |             |
                   v             v
              Valid Events   Invalid Records
                   |             |
                   v             v
              Event Checks    Quarantine
                   |
                   v
              Deduplication
                   |
                   v
          Event Ordering and Processing
                   |
                   v
           SCD Type 2 Transformation
                   |
                   v
               SQLite Database
                   |
                   v
           Customer History Table
                   |
                   v
          Reconciliation and Testing
                   |
                   v
           JSON Validation Report
```

### Processing Flow

1. Read customer events from the input CSV file.
2. Validate the input schema, required fields, email addresses, and timestamps.
3. Separate invalid records and store their validation reasons.
4. Check event IDs to identify exact duplicates and conflicting events.
5. Process accepted events according to their effective timestamps.
6. Detect customer attribute changes using record hashes.
7. Close previous dimension records and insert new versions when changes occur.
8. Store the processed information in SQLite.
9. Run automated tests and reconciliation checks to verify correctness.

---

## 6. Project Structure

```text
scd2-data-pipeline/
│
├── data/
│   └── sample.csv
│
├── docs/
│   ├── data_dictionary.md
│   └── design_tradeoffs.md
│
├── output/
│   └── reconciliation_report.json
│
├── src/
│   ├── __init__.py
│   ├── pipeline.py
│   ├── generate_data.py
│   └── reconcile.py
│
├── tests/
│   └── test_pipeline.py
│
├── README.md
├── PROMPTS.md
├── requirements.txt
└── .gitignore
```

---

## 7. Understanding SCD Type 2

SCD Type 2 is a technique used in data warehousing to preserve historical changes in dimension records.

Instead of updating an existing customer record, a new version is inserted whenever a tracked attribute changes.

### Example

Consider a customer whose city changes from Hyderabad to Bengaluru.

| Customer ID | Name  | City      | Version | Is Current |
|-------------|-------|-----------|---------|------------|
| C101        | Rahul | Hyderabad | 1       | No         |
| C101        | Rahul | Bengaluru | 2       | Yes        |

The first record is retained as historical data, and the second record represents the customer's latest information.

### Important Fields

| Field | Description |
|---|---|
| `customer_id` | Unique identifier for the customer |
| `effective_from` | Timestamp from which the version is valid |
| `effective_to` | Timestamp until which the version is valid |
| `is_current` | Indicates whether the record is the current version |
| `record_hash` | Hash used to identify changes in tracked attributes |

The pipeline tracks changes in the following attributes:

- `name`
- `email`
- `city`

If none of these attributes change, the pipeline avoids creating an unnecessary new version.

---

## 8. Event Processing and Data Integrity

### Duplicate Events

Each incoming event has a unique `event_id`.

- Exact duplicate events are skipped.
- Reusing an event ID with different data is rejected.
- Duplicate events within the same batch are handled.
- Accepted source events are retained in the event ledger.

### Idempotency

The pipeline is designed so that processing the same input repeatedly does not create additional customer dimension versions.

### Late-Arriving Events

Events are processed according to their effective timestamps rather than their arrival order.

When an older event arrives after a newer event, the affected customer's history is reconstructed to maintain the correct chronological sequence.

### Same-Timestamp Events

When multiple events for the same customer have identical effective timestamps, the lexicographically greatest event ID takes precedence.

Both accepted events remain preserved in the source event table.

### Invalid Data

Incoming records are validated before being processed.

Records with missing required values, invalid email addresses, or invalid timestamps are handled separately through quarantine rather than being silently inserted into the customer dimension.

---

## 9. Database Design

The SQLite database maintains separate tables for different responsibilities.

| Table | Responsibility |
|---|---|
| Source Events | Stores accepted incoming customer events. |
| Customer Dimension | Stores current and historical customer versions. |
| Quarantine | Stores rejected records and validation reasons. |
| Pipeline Runs | Tracks pipeline execution details. |

The source event ledger is maintained separately from the customer dimension so that accepted incoming events are preserved independently of the resulting historical versions.

For the complete column definitions, constraints, and data types, refer to the [Data Dictionary](docs/data_dictionary.md).

---

## 10. Installation and Setup

### Prerequisites

- Python 3.10 or later
- Git
- Visual Studio Code or another Python editor

### Step 1: Clone the Repository

```bash
git clone https://github.com/PATHAN-0716/scd2-data-pipeline.git
cd scd2-data-pipeline
```

### Step 2: Create a Virtual Environment

**Windows:**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Linux or macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

The project currently uses Python standard-library modules only, so no external packages need to be installed.

---

## 11. Running the Project

The project contains separate scripts for pipeline processing, synthetic data generation, and reconciliation.

### Main Pipeline

The main implementation is located at:

```text
src/pipeline.py
```

Use the execution entry point defined in this file to process the sample CSV input.

### Generate Synthetic Data

The data generation script is located at:

```text
src/generate_data.py
```

It creates reproducible synthetic customer events using a fixed random seed. The generated data can be used for larger-scale testing.

### Run Automated Tests

Execute the following command from the project root:

```bash
python -m unittest discover -s tests -v
```

### Run Reconciliation

```bash
python -m src.reconcile
```

The reconciliation results are saved to:

```text
output/reconciliation_report.json
```

---

## 12. Automated Testing

The implementation includes twelve automated test scenarios using Python's built-in `unittest` framework.

| No. | Test Scenario |
|---|---|
| 1 | Conflicting duplicate event IDs |
| 2 | Exactly one current dimension record per customer |
| 3 | Duplicate events within a batch |
| 4 | Empty input batches |
| 5 | Late-arriving event history reconstruction |
| 6 | Invalid email quarantine |
| 7 | Missing required fields |
| 8 | Rejection of timestamps without timezone information |
| 9 | No-op updates |
| 10 | Idempotent reprocessing |
| 11 | Same-timestamp event tie-breaking |
| 12 | Unexpected input schema |

Temporary SQLite databases are used during testing so that individual test executions remain isolated.

**Recorded test result:** 12 tests passed.

---

## 13. Benchmark and Reconciliation Results

A synthetic dataset containing 100,000 customer events was used to validate the pipeline against a larger input.

The recorded reconciliation results are:

| Validation | Result |
|---|---|
| Accepted source events | 100,000 |
| Customer dimension records | 79,898 |
| Duplicate dimension versions | 0 |
| Invalid intervals | 0 |
| Customers without exactly one current record | 0 |
| Current flag mismatches | 0 |

**Overall reconciliation status:** Passed

These figures represent the recorded benchmark database results. Repeated executions may correctly report zero newly inserted events because previously accepted events are skipped through duplicate detection.

The reconciliation report provides a machine-readable record of these checks.

---

## 14. Design Decisions and Trade-offs

Some important implementation decisions were made to keep the solution simple and reliable.

### SQLite for storage

SQLite provides persistent relational storage without requiring a separate database server. It is suitable for demonstrating the pipeline and its data integrity requirements.

### Separate source event ledger

Accepted incoming events are stored independently from the customer dimension. This helps preserve the original event history even when multiple events resolve to the same effective timestamp.

### Hash-based change detection

A deterministic hash is generated from tracked customer attributes. This helps identify meaningful changes without unnecessary comparisons.

### Late-arriving event reconstruction

Instead of assuming events always arrive in chronological order, the pipeline reconstructs the affected customer's history when late events are received.

### Deterministic event ordering

A consistent tie-breaking rule is used for events with identical effective timestamps.

### Automated validation

Unit tests and reconciliation checks are used to verify that the customer dimension maintains its historical and current-record invariants.

More details are available in [Design Trade-offs](docs/design_tradeoffs.md).

---

## 15. Scope and Limitations

This project is designed as a focused demonstration of SCD Type 2 data engineering concepts.

The current implementation:

- Uses a local SQLite database.
- Processes CSV-based input.
- Runs as a Python application.
- Does not use distributed processing.
- Does not include a production orchestration or monitoring platform.

For larger production workloads, the design could be extended with a server-based database, distributed processing, scheduling, monitoring, and additional data quality controls.

---

## 16. Repository Contents

| File | Description |
|---|---|
| `src/pipeline.py` | Main CSV ingestion and SCD Type 2 processing logic |
| `src/generate_data.py` | Synthetic customer event generation |
| `src/reconcile.py` | Database integrity and reconciliation checks |
| `tests/test_pipeline.py` | Automated test suite |
| `data/sample.csv` | Sample customer event input |
| `docs/data_dictionary.md` | Database schema documentation |
| `docs/design_tradeoffs.md` | Implementation decisions and limitations |
| `output/reconciliation_report.json` | Recorded reconciliation results |
| `PROMPTS.md` | AI-assisted development prompt history |
| `requirements.txt` | Project dependency information |
| `.gitignore` | Files excluded from version control |

---

## 17. Conclusion

This project demonstrates how customer data can be processed while preserving historical accuracy.

By combining CSV ingestion, validation, event deduplication, chronological processing, SCD Type 2 versioning, automated testing, and reconciliation, the implementation provides a practical example of a reliable data engineering workflow.

The main focus is not just storing customer records, but ensuring that changes are tracked correctly, historical information is retained, and the resulting data can be verified.