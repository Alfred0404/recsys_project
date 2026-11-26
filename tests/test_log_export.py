import csv
from pathlib import Path
from typing import get_args

import pytest

from src.api.main import Interaction
from src.storage.export import export_csv
from src.storage.interactions import initialize, insert_event

APP = Path(__file__).resolve().parents[1] / "web" / "app.js"


def test_every_logged_event_is_sent_by_the_demo():
    # Control: each event the API accepts is emitted by a demo action, so none is dead.
    source = APP.read_text(encoding="utf-8")
    for event in get_args(Interaction.model_fields["event"].annotation):
        assert f'"{event}"' in source, event


def test_export_writes_every_event_and_counts_them(tmp_path):
    db, out = tmp_path / "log.sqlite3", tmp_path / "out" / "log.csv"
    initialize(db)
    for event in ["portfolio_entered", "recommendation_viewed", "feedback_positive"]:
        insert_event(db, "s1", event, None)
    insert_event(db, "s2", "portfolio_entered", "FR0011871128")
    counts = export_csv(db, out)
    with out.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 4 and rows[-1]["isin"] == "FR0011871128"
    assert counts["portfolio_entered"] == 2


def test_export_without_log_fails_clearly(tmp_path):
    with pytest.raises(FileNotFoundError, match="start the API"):
        export_csv(tmp_path / "missing.sqlite3", tmp_path / "out.csv")


def test_export_cannot_replace_the_log_or_an_alias(tmp_path):
    db = tmp_path / "log.sqlite3"
    initialize(db)
    insert_event(db, "s1", "portfolio_entered", None)
    original = db.read_bytes()
    alias = tmp_path / "alias.csv"
    alias.hardlink_to(db)
    journal = tmp_path / "log.sqlite3-wal"

    for output in (db, alias, journal):
        with pytest.raises(ValueError, match="different from the event log"):
            export_csv(db, output)

    assert db.read_bytes() == alias.read_bytes() == original
    assert not journal.exists()


def test_failed_export_keeps_the_previous_csv(tmp_path, monkeypatch):
    db = tmp_path / "log.sqlite3"
    out = tmp_path / "log.csv"
    initialize(db)
    out.write_text("previous CSV", encoding="utf-8")

    def fail_replace(self, destination):
        raise OSError("CSV is locked")

    with monkeypatch.context() as patch:
        patch.setattr(Path, "replace", fail_replace)
        with pytest.raises(OSError, match="CSV is locked"):
            export_csv(db, out)

    assert out.read_text(encoding="utf-8") == "previous CSV"
    assert set(tmp_path.iterdir()) == {db, out}
