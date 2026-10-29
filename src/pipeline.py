import argparse
import csv
import hashlib
import json
import logging
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "output" / "scd2.db"
REQUIRED = ["customer_id", "event_id", "effective_at", "name", "email", "city"]
ATTRS = ["name", "email", "city"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def parse_timestamp(value):
    value = value.strip()
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("effective_at must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def connect(db_path):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS source_events (
        event_id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        effective_at TEXT NOT NULL,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        city TEXT NOT NULL,
        payload_hash TEXT NOT NULL,
        source_file TEXT NOT NULL,
        ingested_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_events_customer_time
        ON source_events(customer_id, effective_at, event_id);

    CREATE TABLE IF NOT EXISTS customer_dimension (
        customer_sk TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        city TEXT NOT NULL,
        attribute_hash TEXT NOT NULL,
        valid_from TEXT NOT NULL,
        valid_to TEXT,
        is_current INTEGER NOT NULL CHECK(is_current IN (0, 1)),
        UNIQUE(customer_id, valid_from),
        CHECK(valid_to IS NULL OR valid_from < valid_to)
    );
    CREATE INDEX IF NOT EXISTS idx_dim_customer
        ON customer_dimension(customer_id, valid_from);

    CREATE TABLE IF NOT EXISTS quarantine (
        reject_id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        source_file TEXT NOT NULL,
        row_number INTEGER NOT NULL,
        raw_record TEXT NOT NULL,
        reason TEXT NOT NULL,
        rejected_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS pipeline_runs (
        run_id TEXT PRIMARY KEY,
        source_file TEXT NOT NULL,
        started_at TEXT NOT NULL,
        ended_at TEXT,
        status TEXT NOT NULL,
        input_count INTEGER NOT NULL DEFAULT 0,
        inserted_events INTEGER NOT NULL DEFAULT 0,
        duplicate_count INTEGER NOT NULL DEFAULT 0,
        rejected_count INTEGER NOT NULL DEFAULT 0,
        dimension_count INTEGER NOT NULL DEFAULT 0,
        duration_ms REAL,
        error TEXT
    );
    """)
    conn.commit()
    return conn


def digest(values):
    raw = json.dumps(values, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_record(row):
    if not isinstance(row, dict):
        raise ValueError("record must be an object")
    missing = [key for key in REQUIRED if key not in row]
    extra = [key for key in row if key not in REQUIRED]
    if missing:
        raise ValueError("missing required fields: " + ", ".join(missing))
    if extra:
        raise ValueError("unexpected fields: " + ", ".join(extra))
    result = {key: (row[key] or "").strip() for key in REQUIRED}
    for key in REQUIRED:
        if not result[key]:
            raise ValueError(f"{key} must not be null or empty")
    result["effective_at"] = parse_timestamp(result["effective_at"])
    if "@" not in result["email"] or result["email"].startswith("@") or result["email"].endswith("@"):
        raise ValueError("email format is invalid")
    return result


def rebuild_customer(conn, customer_id):
    events = conn.execute("""
        SELECT customer_id, event_id, effective_at, name, email, city, payload_hash
        FROM source_events
        WHERE customer_id = ?
        ORDER BY effective_at, event_id
    """, (customer_id,)).fetchall()

    # Same-time events have no intrinsic ordering. Use the documented,
    # deterministic tie-breaker: greatest event_id wins at each timestamp.
    # All source events remain preserved in the immutable event ledger.
    by_timestamp = {}
    for event in events:
        by_timestamp[event["effective_at"]] = event

    # Keep only actual attribute changes; no-op events remain in the event ledger.
    timeline = []
    previous_hash = None
    for event in by_timestamp.values():
        if event["payload_hash"] != previous_hash:
            timeline.append(event)
            previous_hash = event["payload_hash"]

    conn.execute("DELETE FROM customer_dimension WHERE customer_id = ?", (customer_id,))
    for index, event in enumerate(timeline):
        valid_to = timeline[index + 1]["effective_at"] if index + 1 < len(timeline) else None
        conn.execute("""
            INSERT INTO customer_dimension (
                customer_sk, customer_id, name, email, city, attribute_hash,
                valid_from, valid_to, is_current
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            digest([customer_id, event["effective_at"], event["payload_hash"]]),
            customer_id, event["name"], event["email"], event["city"],
            event["payload_hash"], event["effective_at"], valid_to,
            1 if valid_to is None else 0
        ))


def process_records(records, db_path=DEFAULT_DB, source_file="inline"):
    run_id = str(uuid.uuid4())
    started = datetime.now(timezone.utc).isoformat()
    start_clock = time.perf_counter()
    conn = connect(db_path)
    counts = {"input": 0, "inserted": 0, "duplicates": 0, "rejected": 0}
    affected = set()
    seen_in_batch = {}
    error = None
    status = "success"

    try:
        with conn:
            conn.execute("""
                INSERT INTO pipeline_runs(run_id, source_file, started_at, status)
                VALUES (?, ?, ?, 'running')
            """, (run_id, source_file, started))

            for row_number, raw in enumerate(records, start=1):
                counts["input"] += 1
                try:
                    clean = validate_record(raw)
                    payload_hash = digest([clean[k] for k in ATTRS])
                    event_hash = digest(clean)

                    # Conflicting duplicate IDs in one batch are quarantined.
                    event_id = clean["event_id"]
                    if event_id in seen_in_batch:
                        if seen_in_batch[event_id] == event_hash:
                            counts["duplicates"] += 1
                        else:
                            raise ValueError("conflicting duplicate event_id in batch")
                        continue
                    seen_in_batch[event_id] = event_hash

                    existing = conn.execute(
                        "SELECT * FROM source_events WHERE event_id = ?", (event_id,)
                    ).fetchone()
                    if existing:
                        if existing["customer_id"] == clean["customer_id"] and \
                           existing["effective_at"] == clean["effective_at"] and \
                           existing["payload_hash"] == payload_hash and \
                           all(existing[k] == clean[k] for k in ATTRS):
                            counts["duplicates"] += 1
                            continue
                        raise ValueError("event_id already exists with different content")

                    conn.execute("""
                        INSERT INTO source_events (
                            event_id, customer_id, effective_at, name, email, city,
                            payload_hash, source_file, ingested_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        clean["event_id"], clean["customer_id"], clean["effective_at"],
                        clean["name"], clean["email"], clean["city"], payload_hash,
                        source_file, datetime.now(timezone.utc).isoformat()
                    ))
                    counts["inserted"] += 1
                    affected.add(clean["customer_id"])

                except (ValueError, TypeError, AttributeError) as exc:
                    counts["rejected"] += 1
                    conn.execute("""
                        INSERT INTO quarantine(
                            run_id, source_file, row_number, raw_record, reason, rejected_at
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        run_id, source_file, row_number,
                        json.dumps(raw, default=str, sort_keys=True),
                        str(exc), datetime.now(timezone.utc).isoformat()
                    ))

            for customer_id in sorted(affected):
                rebuild_customer(conn, customer_id)

            dimension_count = conn.execute(
                "SELECT COUNT(*) FROM customer_dimension"
            ).fetchone()[0]
            conn.execute("""
                UPDATE pipeline_runs SET ended_at=?, status=?, input_count=?,
                    inserted_events=?, duplicate_count=?, rejected_count=?,
                    dimension_count=?, duration_ms=?, error=?
                WHERE run_id=?
            """, (
                datetime.now(timezone.utc).isoformat(), status, counts["input"],
                counts["inserted"], counts["duplicates"], counts["rejected"],
                dimension_count, round((time.perf_counter()-start_clock)*1000, 2),
                error, run_id
            ))
    except Exception as exc:
        status = "failed"
        error = str(exc)
        logger.exception("Pipeline run failed: %s", run_id)
        # The transaction rolls back; record the failed run separately.
        with conn:
            conn.execute("""
                INSERT OR REPLACE INTO pipeline_runs(
                    run_id, source_file, started_at, ended_at, status,
                    input_count, inserted_events, duplicate_count,
                    rejected_count, duration_ms, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id, source_file, started,
                datetime.now(timezone.utc).isoformat(), status,
                counts["input"], counts["inserted"], counts["duplicates"],
                counts["rejected"], round((time.perf_counter()-start_clock)*1000, 2),
                error
            ))
    finally:
        conn.close()

    result = {"run_id": run_id, "status": status, **counts, "error": error}
    logger.info("Run result: %s", json.dumps(result))
    if status != "success":
        raise RuntimeError(f"Pipeline failed; run_id={run_id}; error={error}")
    return result


def process_csv(csv_path, db_path=DEFAULT_DB):
    csv_path = Path(csv_path)
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != REQUIRED:
            raise ValueError(
                f"Unexpected CSV schema. Expected {REQUIRED}; got {reader.fieldnames}"
            )
        return process_records(reader, db_path, str(csv_path))


def main():
    parser = argparse.ArgumentParser(description="SCD Type 2 customer dimension pipeline")
    parser.add_argument("--input", required=True, help="Input CSV path")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="SQLite database path")
    args = parser.parse_args()
    print(json.dumps(process_csv(args.input, args.db), indent=2))


if __name__ == "__main__":
    main()
