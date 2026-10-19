from __future__ import annotations

from dataclasses import dataclass, field

from thusa.raw import RawFile


@dataclass
class IngestResult:
    source_id: str
    status: str = "ok"  # ok | unchanged | partial | failed | blocked | awaiting_manual_drop
    files: list[RawFile] = field(default_factory=list)
    requests: int = 0
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "source_id": self.source_id,
            "status": self.status,
            "files": len(self.files),
            "new_files": sum(1 for f in self.files if f.status == "ok"),
            "bytes": sum(f.bytes for f in self.files),
            "requests": self.requests,
            "errors": self.errors,
            "notes": self.notes,
        }
