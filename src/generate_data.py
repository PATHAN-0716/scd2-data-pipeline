import csv
import random
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

FIELDS = ["customer_id", "event_id", "effective_at", "name", "email", "city"]


def generate(output, count=1000, seed=42):
    rng = random.Random(seed)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)

    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for i in range(count):
            customer = f"C{rng.randint(1, max(1, count // 5)):06d}"
            event_num = i + 1
            timestamp = base + timedelta(hours=rng.randint(0, max(1, count)))
            writer.writerow({
                "customer_id": customer,
                "event_id": f"E{event_num:08d}",
                "effective_at": timestamp.isoformat().replace("+00:00", "Z"),
                "name": f"Customer {customer}",
                "email": f"{customer.lower()}@example.com",
                "city": rng.choice(["Hyderabad", "Kakinada", "Chennai", "Bengaluru"])
            })
    print(f"Generated {count} records at {output} (seed={seed})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="data/generated.csv")
    args = parser.parse_args()
    if args.count < 0:
        parser.error("--count must be non-negative")
    generate(args.output, args.count, args.seed)
