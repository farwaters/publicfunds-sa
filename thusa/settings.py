"""Paths and configuration. Everything is relative to the repo root unless THUSA_ROOT is set."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Paths:
    root: Path

    @property
    def data(self) -> Path:
        return self.root / "data"

    @property
    def raw(self) -> Path:
        return self.data / "raw"

    @property
    def drop(self) -> Path:
        """Manual-drop folder for sources that cannot be fetched by script (e.g. PPD Power BI export)."""
        return self.data / "drop"

    @property
    def staging_files(self) -> Path:
        return self.data / "staging"

    @property
    def warehouse(self) -> Path:
        return self.data / "thusa.duckdb"

    @property
    def dist(self) -> Path:
        return self.root / "dist"

    @property
    def seed(self) -> Path:
        """Raw research downloads from 19 Oct 2026 (git-ignored); used only as an offline fallback."""
        return self.root / "src"


def get_paths(root: Path | None = None) -> Paths:
    return Paths(Path(root or os.environ.get("THUSA_ROOT") or REPO_ROOT))


def load_yaml(name: str) -> dict:
    with open(REPO_ROOT / "config" / name, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def detector_config() -> dict:
    return load_yaml("detectors.yaml")["detectors"]


def hmac_secret() -> bytes:
    """Key for hashing SA ID numbers (POPIA). Env THUSA_HMAC_KEY (hex) or a 0600 file outside the repo.
    Never logged, printed or committed."""
    env = os.environ.get("THUSA_HMAC_KEY")
    if env:
        return bytes.fromhex(env)
    path = Path(os.environ.get("THUSA_HMAC_KEY_FILE", Path.home() / ".config" / "thusa" / "hmac.key"))
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as fh:
            fh.write(os.urandom(32))
    return path.read_bytes()
