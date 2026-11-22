"""Export the demo event log to CSV and print a count per event.

Usage: python -m src.storage.export [--db dataset/interactions.sqlite3] [--out dataset/interactions.csv]
"""
import argparse
import csv
import sqlite3
from collections import Counter
from contextlib import closing
from pathlib import Path


def export_csv(db: Path, out: Path) -> Counter:
    if not db.is_file():
        raise FileNotFoundError(f"No event log at {db}: start the API and use the demo first.")
    with closing(sqlite3.connect(db)) as conn:
        cursor = conn.execute("SELECT id, timestamp, session_id, event, isin FROM interactions ORDER BY id")
        header = [c[0] for c in cursor.description]
        rows = cursor.fetchall()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows([header, *rows])
    return Counter(row[3] for row in rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("dataset/interactions.sqlite3"))
    parser.add_argument("--out", type=Path, default=Path("dataset/interactions.csv"))
    args = parser.parse_args()
    counts = export_csv(args.db, args.out)
    print(f"{sum(counts.values())} events written to {args.out}")
    for event, n in counts.most_common():
        print(f"  {event}: {n}")
