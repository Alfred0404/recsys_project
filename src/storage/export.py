"""Export the demo event log to CSV and print a count per event.

Usage: python -m src.storage.export [--db dataset/interactions.sqlite3] [--out dataset/interactions.csv]
"""
import argparse
import csv
import sqlite3
from collections import Counter
from contextlib import closing
from pathlib import Path
from tempfile import NamedTemporaryFile


def export_csv(db: Path, out: Path) -> Counter:
    if not db.is_file():
        raise FileNotFoundError(f"No event log at {db}: start the API and use the demo first.")
    db = db.resolve()
    out = out.resolve()
    protected = [db, *(db.with_name(db.name + suffix) for suffix in ("-journal", "-wal", "-shm"))]
    if any(out == path or (out.exists() and path.exists() and out.samefile(path)) for path in protected):
        raise ValueError("CSV output must be different from the event log database and its SQLite files.")

    with closing(sqlite3.connect(f"{db.as_uri()}?mode=ro", uri=True)) as conn:
        cursor = conn.execute("SELECT id, timestamp, session_id, event, isin FROM interactions ORDER BY id")
        header = [c[0] for c in cursor.description]
        rows = cursor.fetchall()
    out.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(mode="w", newline="", encoding="utf-8", dir=out.parent,
                                prefix=".log-export-", suffix=".tmp", delete=False) as f:
            temporary = Path(f.name)
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
        temporary.replace(out)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
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
