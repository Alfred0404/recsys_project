"""Download and unzip FAR-Trans into dataset/FAR-Trans/

Usage: python -m src.data.download
Source: Sanz-Cruzado, Droukas & McCreadie, IJCAI 2024 Fin-RecSys, doi.org/10.5525/gla.researchdata.1658 (CC BY 4.0).
"""
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from src.data.load_and_check import DATE_COLS, RAW

URL = "https://researchdata.gla.ac.uk/1658/1/FAR-Trans.zip"
EXPECTED = [f"{name}.csv" for name in DATE_COLS] + ["questionnaires.csv"]


def missing_files(dest: Path) -> list[str]:
    return [f for f in EXPECTED if not (dest / f).is_file()]


def download(url: str = URL, dest: Path = RAW) -> Path:
    if not missing_files(dest):
        print(f"FAR-Trans already in {dest}, nothing to do.")
        return dest

    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / "FAR-Trans.zip"
        print(f"Downloading {url} ...")
        urllib.request.urlretrieve(url, archive)

        with zipfile.ZipFile(archive) as z:
            z.extractall(dest.parent)  # the archive holds a FAR-Trans/ folder

    if missing := missing_files(dest):
        raise FileNotFoundError(f"Archive extracted but files are missing in {dest}: {missing}")

    print(f"FAR-Trans ready in {dest}.")

    return dest


if __name__ == "__main__":
    download()
