"""Raw layer: immutable, dated, checksummed files plus an append-only manifest.

Layout: data/raw/<source_id>/<YYYY-MM-DD>/<name>  (+ manifest at data/raw/manifest.jsonl)
Idempotency: a file whose bytes match the latest stored copy of the same (source, name) is not
rewritten; the manifest records status 'unchanged' and points at the existing file.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


@dataclass
class RawFile:
    source_id: str
    name: str
    url: str
    path: str  # relative to data/raw
    sha256: str
    bytes: int
    fetched_at_utc: str  # when these bytes were first retrieved
    checked_at_utc: str  # when we last confirmed them
    http_status: int | None
    status: str  # ok | unchanged


class RawStore:
    def __init__(self, raw_dir: Path, now=utcnow, resume: bool = True) -> None:
        self.resume = resume  # False = always refetch (bytes still deduplicated by checksum)
        self.dir = Path(raw_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.manifest = self.dir / "manifest.jsonl"
        self.now = now

    # -- manifest -------------------------------------------------------------
    def entries(self) -> list[RawFile]:
        if not self.manifest.exists():
            return []
        out = []
        with open(self.manifest, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    out.append(RawFile(**json.loads(line)))
        return out

    def latest(self, source_id: str, name: str) -> RawFile | None:
        hits = [e for e in self.entries() if e.source_id == source_id and e.name == name]
        return hits[-1] if hits else None

    def latest_files(self, source_id: str) -> list[RawFile]:
        """Latest entry per name for a source (what the loaders should read)."""
        seen: dict[str, RawFile] = {}
        for e in self.entries():
            if e.source_id == source_id:
                seen[e.name] = e
        return list(seen.values())

    def _append(self, rf: RawFile) -> None:
        with open(self.manifest, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(rf), sort_keys=True) + "\n")

    # -- writes ---------------------------------------------------------------
    def fresh_today(self, source_id: str, name: str) -> RawFile | None:
        """Return today's copy if one exists (lets an interrupted run resume without refetching)."""
        if not self.resume:
            return None
        e = self.latest(source_id, name)
        if e and e.checked_at_utc[:10] == self.now().date().isoformat() and (self.dir / e.path).exists():
            return e
        return None

    def save(self, source_id: str, name: str, content: bytes, url: str, http_status: int | None = 200) -> RawFile:
        now = self.now()
        sha = sha256_bytes(content)
        prev = self.latest(source_id, name)
        if prev and prev.sha256 == sha and (self.dir / prev.path).exists():
            rf = RawFile(source_id, name, url, prev.path, sha, len(content), prev.fetched_at_utc,
                         now.isoformat(), http_status, "unchanged")
            self._append(rf)
            return rf
        rel = Path(source_id) / now.date().isoformat() / name
        dest = self.dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        tmp.write_bytes(content)
        os.replace(tmp, dest)
        dest.with_name(dest.name + ".sha256").write_text(f"{sha}  {dest.name}\n")
        rf = RawFile(source_id, name, url, str(rel), sha, len(content), now.isoformat(), now.isoformat(),
                     http_status, "ok")
        self._append(rf)
        return rf

    def save_file(self, source_id: str, name: str, src: Path, url: str) -> RawFile:
        return self.save(source_id, name, Path(src).read_bytes(), url, None)

    def path_of(self, rf: RawFile) -> Path:
        return self.dir / rf.path


def log_run(raw_dir: Path, record: dict) -> None:
    """Append an ingest-run record (loaded into ops.ingest_run at build time)."""
    with open(Path(raw_dir) / "runs.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True, default=str) + "\n")
