# Design and Trade-offs

## Architecture
Python reads CSV input, validates records, detects duplicates, writes accepted
events to SQLite, rebuilds affected customer histories, and records operational
metrics and rejects.

## History model
The source event ledger preserves accepted events. Dimension intervals are
half-open: valid_from is inclusive and valid_to is exclusive. The current
version has a NULL valid_to and is_current = 1.

## Change detection
SHA-256 hashes of tracked attributes identify changes. No-op events remain in
the event ledger without creating additional dimension versions.

## Late-arriving data
The affected customer's timeline is rebuilt from all accepted events ordered
by effective timestamp. This prioritizes correctness and simplicity.

## Same-time events
The lexicographically greatest event ID wins for a customer/timestamp because
the source schema does not provide an authoritative sequence number. All events
remain in the ledger.

## Stable keys
Dimension version IDs are deterministic hashes of the customer key, effective
timestamp, and attribute hash.

## Recovery
Accepted events and dimension rebuilds are transactional. Identical event
replays are skipped. Invalid records are quarantined for correction.

## Limitations
This is a local, single-process SQLite implementation. Full customer timeline
rebuilds may be expensive for very long histories. Email validation is basic.
Incremental timeline repair is a potential optimization after profiling.
