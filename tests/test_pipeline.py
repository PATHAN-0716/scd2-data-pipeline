import sys
import tempfile
import unittest
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.pipeline import process_records, connect

def event(event_id, when, city="Hyderabad", customer="C1", name="Asha", email="asha@example.com"):
    return {
        "customer_id": customer,
        "event_id": event_id,
        "effective_at": when,
        "name": name,
        "email": email,
        "city": city,
    }


class SCD2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "test.db"

    def tearDown(self):
        self.temp.cleanup()

    def rows(self, query, args=()):
        conn = connect(self.db)
        try:
            return [dict(r) for r in conn.execute(query, args).fetchall()]
        finally:
            conn.close()

    def test_happy_path_and_late_arriving_event(self):
        process_records([
            event("e1", "2025-01-01T00:00:00Z", "Hyderabad"),
            event("e3", "2025-02-01T00:00:00Z", "Chennai"),
        ], self.db)
        process_records([
            event("e2", "2025-01-15T00:00:00Z", "Bengaluru"),
        ], self.db)

        rows = self.rows(
            "SELECT * FROM customer_dimension WHERE customer_id='C1' ORDER BY valid_from"
        )
        self.assertEqual([r["city"] for r in rows], ["Hyderabad", "Bengaluru", "Chennai"])
        self.assertEqual(rows[0]["valid_to"], "2025-01-15T00:00:00.000000Z")
        self.assertEqual(rows[1]["valid_to"], "2025-02-01T00:00:00.000000Z")
        self.assertEqual(rows[2]["valid_to"], None)
        self.assertEqual([r["is_current"] for r in rows], [0, 0, 1])

    def test_rerun_is_idempotent(self):
        records = [event("e1", "2025-01-01T00:00:00Z")]
        process_records(records, self.db)
        result = process_records(records, self.db)
        self.assertEqual(result["duplicates"], 1)
        self.assertEqual(len(self.rows("SELECT * FROM source_events")), 1)
        self.assertEqual(len(self.rows("SELECT * FROM customer_dimension")), 1)

    def test_duplicate_in_same_batch(self):
        record = event("e1", "2025-01-01T00:00:00Z")
        result = process_records([record, record], self.db)
        self.assertEqual(result["inserted"], 1)
        self.assertEqual(result["duplicates"], 1)

    def test_invalid_email_is_quarantined(self):
        result = process_records([
            event("e1", "2025-01-01T00:00:00Z", email="not-an-email")
        ], self.db)
        self.assertEqual(result["rejected"], 1)
        self.assertEqual(len(self.rows("SELECT * FROM quarantine")), 1)
        self.assertEqual(len(self.rows("SELECT * FROM source_events")), 0)

    def test_missing_field_is_quarantined(self):
        record = event("e1", "2025-01-01T00:00:00Z")
        del record["name"]
        result = process_records([record], self.db)
        self.assertEqual(result["rejected"], 1)

    def test_empty_batch(self):
        result = process_records([], self.db)
        self.assertEqual(result["input"], 0)
        self.assertEqual(result["inserted"], 0)
        self.assertEqual(result["status"], "success")

    def test_naive_timestamp_is_rejected(self):
        result = process_records([
            event("e1", "2025-01-01T00:00:00")
        ], self.db)
        self.assertEqual(result["rejected"], 1)

    def test_conflicting_event_id_is_rejected(self):
        first = event("e1", "2025-01-01T00:00:00Z", "Hyderabad")
        conflicting = event("e1", "2025-01-01T00:00:00Z", "Chennai")
        result = process_records([first, conflicting], self.db)
        self.assertEqual(result["inserted"], 1)
        self.assertEqual(result["rejected"], 1)

    def test_no_op_update_does_not_create_dimension_version(self):
        process_records([
            event("e1", "2025-01-01T00:00:00Z", "Hyderabad"),
            event("e2", "2025-01-02T00:00:00Z", "Hyderabad"),
        ], self.db)
        rows = self.rows("SELECT * FROM customer_dimension WHERE customer_id='C1'")
        self.assertEqual(len(rows), 1)

    def test_unexpected_schema_is_not_silently_accepted(self):
        from src.pipeline import validate_record
        record = event("e1", "2025-01-01T00:00:00Z")
        record["unexpected_column"] = "value"
        with self.assertRaises(ValueError):
            validate_record(record)

    def test_current_row_invariant(self):
        process_records([
            event("e1", "2025-01-01T00:00:00Z", "Hyderabad"),
            event("e2", "2025-01-02T00:00:00Z", "Chennai"),
        ], self.db)
        rows = self.rows("SELECT * FROM customer_dimension WHERE customer_id='C1'")
        self.assertEqual(sum(r["is_current"] for r in rows), 1)
        for row in rows[:-1]:
            self.assertIsNotNone(row["valid_to"])


    def test_same_timestamp_uses_deterministic_event_id_tiebreaker(self):
        process_records([
            event("e1", "2025-01-01T00:00:00Z", "Hyderabad"),
            event("e2", "2025-01-01T00:00:00Z", "Chennai"),
        ], self.db)

        rows = self.rows(
            "SELECT * FROM customer_dimension WHERE customer_id='C1'"
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["city"], "Chennai")
        self.assertEqual(rows[0]["is_current"], 1)
        self.assertEqual(len(self.rows("SELECT * FROM source_events")), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
