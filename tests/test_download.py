import zipfile

import pytest

from src.data.download import EXPECTED, download


def make_zip(path, files):
    with zipfile.ZipFile(path, "w") as z:
        for f in files:
            z.writestr(f"FAR-Trans/{f}", "col\n1\n")
    return path.as_uri()  # urllib reads file:// URLs, so no network needed


def test_download_extracts_then_skips(tmp_path):
    url = make_zip(tmp_path / "ok.zip", EXPECTED)
    dest = tmp_path / "dataset" / "FAR-Trans"
    download(url, dest)
    assert all((dest / f).is_file() for f in EXPECTED)
    download("file:///does/not/exist.zip", dest)  # already there: must not fetch


def test_download_fails_on_incomplete_archive(tmp_path):
    url = make_zip(tmp_path / "bad.zip", EXPECTED[:-1])
    with pytest.raises(FileNotFoundError, match="questionnaires.csv"):
        download(url, tmp_path / "dataset" / "FAR-Trans")
