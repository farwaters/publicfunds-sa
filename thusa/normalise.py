"""Pure normalisation helpers. Rule: unknown stays None; never coerce a missing value to 0."""
from __future__ import annotations

import hashlib
import hmac
import re
import unicodedata
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

_NULL_TOKENS = {"", "null", "none", "n/a", "na", "-", "nan"}


def to_cents(value, unit_multiplier: int = 1) -> int | None:
    """Rand amount (number or string, optionally in R thousands via unit_multiplier) -> integer cents.

    None/blank/'N/A' -> None (unknown). '0' -> 0 (a reported zero). Handles 'R 1 234,50', '1,234.50', '(500)'.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        raise TypeError("boolean is not money")
    if isinstance(value, (int, float, Decimal)):
        if isinstance(value, float) and value != value:  # NaN
            return None
        d = Decimal(str(value))
    else:
        s = str(value).strip()
        if s.lower() in _NULL_TOKENS:
            return None
        neg = s.startswith("(") and s.endswith(")")
        s = s.strip("()").replace("R", "").replace("\u00a0", "").replace(" ", "")
        if "," in s and "." in s:
            s = s.replace(",", "")
        elif "," in s:
            # thousands comma ("1,234" / "1,234,567": every group 3 digits) vs SA decimal comma ("1234,50", "1,5")
            groups = s.lstrip("-").split(",")
            if len(groups) > 1 and all(len(g) == 3 for g in groups[1:]) and 1 <= len(groups[0]) <= 3:
                s = s.replace(",", "")
            else:
                head, _, tail = s.rpartition(",")
                s = f"{head.replace(',', '')}.{tail}"
        try:
            d = Decimal(s)
        except InvalidOperation as exc:
            raise ValueError(f"not a money value: {value!r}") from exc
        if neg:
            d = -d
    return int((d * unit_multiplier * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


OCDS_IMPLAUSIBLE_HIGH_CENTS = 20_000_000_000 * 100  # R20bn per award; above this the value is kept but excluded


def ocds_value_cents(amount) -> tuple[int | None, str | None]:
    """OCDS value -> (cents, quality_note). eTenders publishes 0 as a placeholder, so 0 => unknown."""
    if amount is None:
        return None, "missing"
    cents = to_cents(amount)
    if cents is None:
        return None, "missing"
    if cents <= 0:
        return None, "zero_placeholder"
    if cents < 100_00:  # below R100: almost certainly a placeholder (e.g. R10), kept but marked
        return cents, "implausible_low"
    if cents > OCDS_IMPLAUSIBLE_HIGH_CENTS:  # e.g. R370bn for one SANRAL road contract: likely a capture error
        return cents, "implausible_high"
    return cents, None


_LEGAL_SUFFIXES = [
    r"\(pty\)\s*ltd", r"\bpty\s*ltd\b", r"\(pty\)", r"\bproprietary limited\b", r"\blimited\b", r"\bltd\b",
    r"\bcc\b", r"\bnpc\b", r"\binc(orporated)?\b", r"\bsoc\b", r"\b\(rf\)\b", r"\bjv\b",
]
_STOP = {"the", "and", "of"}


def norm_name(name: str | None) -> str | None:
    """Normalise an organisation name for exact-key matching (case, accents, punctuation, legal suffixes)."""
    if name is None:
        return None
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower()
    s = s.replace("&", " and ")
    for pat in _LEGAL_SUFFIXES:
        s = re.sub(pat, " ", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    toks = [t for t in s.split() if t not in _STOP]
    return " ".join(toks) or None


def person_key(name: str | None) -> str | None:
    """'SURNAME, Given Names' and 'Given Names Surname' -> sorted-token key for person matching."""
    if not name:
        return None
    s = norm_name(name.replace(",", " "))
    return " ".join(sorted(s.split())) if s else None


_REG_RE = re.compile(r"^(\d{4})/(\d{6})/(\d{2})$")
_ID_RE = re.compile(r"^\d{13}$")


def classify_identifier(raw: str | None) -> tuple[str, str | None]:
    """Return (kind, normalised) where kind in {'cipc_reg','sa_id','other','none'}."""
    if raw is None or not str(raw).strip():
        return "none", None
    s = re.sub(r"\s+", "", str(raw))
    if _REG_RE.match(s):
        return "cipc_reg", s
    if _ID_RE.match(s):
        return "sa_id", s
    return "other", s


def hmac_id(secret: bytes, sa_id: str) -> str:
    """Keyed hash of an SA ID number for matching only (POPIA). The raw number is never stored in curated."""
    return hmac.new(secret, sa_id.encode(), hashlib.sha256).hexdigest()


def municipal_fy_label(fy_end_year: int) -> str:
    """Municipal FY ends 30 June: FYE 2024 -> '2023/24'."""
    return f"{fy_end_year - 1}/{str(fy_end_year)[-2:]}"


def national_fy_label(fy_start_year: int) -> str:
    """National FY starts 1 April: 2025 -> '2025/26'."""
    return f"{fy_start_year}/{str(fy_start_year + 1)[-2:]}"


def municipal_fye_for_date(d: date | datetime) -> int:
    """Date -> municipal financial-year-end year (July..June)."""
    return d.year + 1 if d.month >= 7 else d.year


def parse_date(s) -> date | None:
    if s is None:
        return None
    s = str(s).strip()
    if not s or s.startswith("0001-01-01"):
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d").date()
        except ValueError:
            return None


_MUNI_NOISE = [
    r"\bmetropolitan\b", r"\bmetro\b", r"\blocal\b", r"\bmunicipality\b", r"\bmunicipal\b", r"\bcity\b",
    r"\bdistrict\b", r"\bcouncil\b", r"\bmunisipaliteit\b", r"\bplaaslike\b", r"\bdm\b", r"\blm\b",
]


def muni_key(name: str | None) -> str | None:
    """Key for matching a buyer name (e.g. 'Stellenbosch Municipality') to a municipality name."""
    s = norm_name(name)
    if not s:
        return None
    for pat in _MUNI_NOISE:
        s = re.sub(pat, " ", s)
    toks = s.split()
    # collapse initials: 'o r tambo' == 'or tambo'
    merged: list[str] = []
    for tok in toks:
        if len(tok) == 1 and merged and len(merged[-1]) <= 2 and merged[-1].isalpha() and tok.isalpha():
            merged[-1] += tok
        else:
            merged.append(tok)
    return " ".join(merged) or None
