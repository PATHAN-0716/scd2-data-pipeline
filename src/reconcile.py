import sqlite3
import json
import sys
from pathlib import Path

db_path = Path("output/benchmark.db")
if not db_path.exists():
    raise SystemExit("Run the 100,000-row benchmark first.")

db = sqlite3.connect(db_path)
checks = {
    "duplicate_dimension_versions": """
        SELECT COUNT(*) FROM (
            SELECT customer_id, valid_from
            FROM customer_dimension
            GROUP BY customer_id, valid_from
            HAVING COUNT(*) > 1
        )
    """,
    "invalid_intervals": """
        SELECT COUNT(*) FROM customer_dimension
        WHERE valid_to IS NOT NULL AND valid_from >= valid_to
    """,
    "customers_without_one_current_row": """
        SELECT COUNT(*) FROM (
            SELECT customer_id FROM customer_dimension
            GROUP BY customer_id HAVING SUM(is_current) != 1
        )
    """,
    "current_flag_mismatch": """
        SELECT COUNT(*) FROM customer_dimension
        WHERE (valid_to IS NULL AND is_current != 1)
           OR (valid_to IS NOT NULL AND is_current != 0)
    """
}
report = {key: db.execute(sql).fetchone()[0] for key, sql in checks.items()}
report["source_event_count"] = db.execute(
    "SELECT COUNT(*) FROM source_events"
).fetchone()[0]
report["dimension_row_count"] = db.execute(
    "SELECT COUNT(*) FROM customer_dimension"
).fetchone()[0]
report["all_checks_passed"] = all(report[key] == 0 for key in checks)

Path("output/reconciliation_report.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)
db.close()
print(json.dumps(report, indent=2))

if not report["all_checks_passed"]:
    sys.exit("Reconciliation failed.")
