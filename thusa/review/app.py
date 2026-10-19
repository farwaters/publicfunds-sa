"""Thusa review web app (FastAPI + Jinja2 + HTMX). Binds to 127.0.0.1 by default; see runbook RB-08.

Every page except /login, /healthz and /static needs a signed-in reviewer: the queue contains unreviewed
allegations about named suppliers, so nothing here is anonymous (ADR-0005, ADR-0008).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from urllib.parse import quote

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from thusa.review import security as sec
from thusa.review import workflow as wf
from thusa.review.service import Service, to_csv
from thusa.review.store import SAST, sast_label
from thusa.review.warehouse import DATA_TYPES, SEVERITIES, TYPE_LABEL, WarehouseMissing, rand
from thusa.settings import Paths, get_paths

HERE = Path(__file__).parent
MAX_BODY = 64 * 1024
PAGE = 50
SAFE_SCHEMES = ("https://", "http://")


def _safe_url(u):
    return u if isinstance(u, str) and u.startswith(SAFE_SCHEMES) else None


def _fmt_ts(v):
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v.astimezone(SAST).strftime("%Y-%m-%d %H:%M SAST")
    return sast_label(str(v))


class DecisionIn(BaseModel):
    decision: Literal["confirm", "reject", "needs_info", "escalate"]
    reason: str = Field(min_length=wf.REASON_MIN, max_length=wf.REASON_MAX)
    notes: str | None = Field(default=None, max_length=wf.NOTES_MAX)
    channel: Literal["api", "bot"] = "api"


def create_app(paths: Paths | None = None, allowed_hosts: list[str] | None = None,
               secure_cookies: bool | None = None) -> FastAPI:
    paths = paths or get_paths()
    svc = Service(paths)
    secure = (os.environ.get("THUSA_REVIEW_SECURE_COOKIES") == "1") if secure_cookies is None else secure_cookies
    hosts = allowed_hosts or [h.strip() for h in os.environ.get(
        "THUSA_REVIEW_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if h.strip()]
    cookie = "__Host-pf_session" if secure else "pf_session"
    login_cookie = "__Host-pf_login_csrf" if secure else "pf_login_csrf"

    app = FastAPI(title="Thusa review", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.service = svc
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts)

    @app.middleware("http")
    async def headers_and_limits(request: Request, call_next):
        cl = request.headers.get("content-length")
        if cl and (not cl.isdigit() or int(cl) > MAX_BODY):
            return PlainTextResponse("Request body too large", status_code=413)
        resp = await call_next(request)
        h = resp.headers
        h["Content-Security-Policy"] = ("default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' "
                                        "data:; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; "
                                        "base-uri 'none'")
        h["X-Content-Type-Options"] = "nosniff"
        h["X-Frame-Options"] = "DENY"
        h["Referrer-Policy"] = "no-referrer"
        h["Permissions-Policy"] = "geolocation=(), camera=(), microphone=(), payment=(), usb=()"
        h["Cross-Origin-Opener-Policy"] = "same-origin"
        h["Cross-Origin-Resource-Policy"] = "same-origin"
        if not request.url.path.startswith("/static/"):
            h["Cache-Control"] = "no-store"
        if secure:
            h["Strict-Transport-Security"] = "max-age=31536000"
        return resp

    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
    tpl = Jinja2Templates(directory=HERE / "templates")
    tpl.env.filters.update(rand=rand, sast=_fmt_ts, safe_url=_safe_url, tojson_pretty=lambda v: json.dumps(
        v, indent=1, ensure_ascii=False, default=str))
    tpl.env.globals.update(TYPE_LABEL=TYPE_LABEL, DECISION_LABELS=wf.DECISION_LABELS, STATUSES=wf.STATUSES)

    # ------------------------------------------------------------------ auth helpers
    def client_ip(request: Request) -> str:
        return request.client.host if request.client else "unknown"

    def current_user(request: Request) -> dict | None:
        raw = request.cookies.get(cookie)
        if not raw or len(raw) > 128:
            return None
        h = sec.sha256_hex(raw)
        s = svc.store.get_session(h)
        if not sec.session_valid(s):
            return None
        svc.store.touch_session(h)
        s["session_hash"] = h
        return s

    def page_user(request: Request) -> dict:
        u = current_user(request)
        if not u:
            nxt = request.url.path + (f"?{request.url.query}" if request.url.query else "")
            raise HTTPException(status_code=303, headers={"Location": "/login?next=" + quote(nxt, safe="")})
        return u

    def form_user(request: Request) -> dict:
        u = current_user(request)
        if not u:
            raise HTTPException(status_code=401, detail="Sign in first")
        return u

    def check_csrf(u: dict, token: str | None) -> None:
        if not sec.same(token, u["csrf_token"]):
            raise HTTPException(status_code=403, detail="CSRF token missing or invalid")

    def api_user(request: Request) -> dict:
        auth = request.headers.get("authorization", "")
        ip = client_ip(request)
        if sec.rate_limited(svc.store, "api-token", ip):
            raise HTTPException(status_code=429, detail="Too many failed attempts", headers={"Retry-After": "900"})
        tok = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
        r = svc.store.get_reviewer_by_token_hash(sec.sha256_hex(tok)) if tok.startswith(sec.TOKEN_PREFIX) else None
        if not r:
            svc.store.record_attempt([f"ip:{ip}"], ok=False)
            raise HTTPException(status_code=401, detail="Valid bearer token required",
                                headers={"WWW-Authenticate": "Bearer"})
        return r

    def render(request, name, ctx, status=200, user=None):
        ctx = {"request": request, "user": user, **ctx}
        return tpl.TemplateResponse(request, name, ctx, status_code=status)

    @app.exception_handler(HTTPException)
    async def http_exc(request: Request, exc: HTTPException):
        if exc.status_code == 303:
            return RedirectResponse(exc.headers["Location"], status_code=303)
        if request.url.path.startswith("/api/") or request.url.path == "/healthz":
            return JSONResponse({"error": exc.detail}, status_code=exc.status_code, headers=exc.headers)
        return render(request, "error.html", {"status": exc.status_code, "detail": exc.detail}, exc.status_code)

    @app.exception_handler(WarehouseMissing)
    async def no_wh(request: Request, exc: WarehouseMissing):
        return PlainTextResponse("Warehouse not built yet: run `uv run thusa build`.", status_code=503)

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon():
        return Response(status_code=204)

    # ------------------------------------------------------------------ health
    @app.get("/healthz")
    def healthz():
        bid = svc.wh.build_id()
        chain = svc.store.verify_chain()
        ok = bid is not None and chain["ok"]
        return JSONResponse({"status": "ok" if ok else "degraded", "warehouse_build_id": bid,
                             "review_db": "ok", "decisions": chain["n"], "audit_chain_ok": chain["ok"]},
                            status_code=200 if ok else 503)

    # ------------------------------------------------------------------ login / logout
    @app.get("/login", response_class=HTMLResponse)
    def login_form(request: Request, next: str = "/flags"):
        token = sec.new_session()[2]
        resp = render(request, "login.html", {"csrf": token, "next": _safe_next(next), "error": None})
        resp.set_cookie(login_cookie, token, httponly=True, samesite="strict", secure=secure, max_age=1800, path="/")
        return resp

    @app.post("/login")
    def login(request: Request, username: str = Form(max_length=64), password: str = Form(max_length=256),
              csrf_token: str = Form(max_length=128), next: str = Form("/flags", max_length=512)):
        if not sec.same(csrf_token, request.cookies.get(login_cookie)):
            raise HTTPException(status_code=403, detail="CSRF token missing or invalid - reload the sign-in page")
        username, ip = username.strip().lower(), client_ip(request)
        new_csrf = sec.new_session()[2]

        def fail(msg, status):
            r = render(request, "login.html", {"csrf": new_csrf, "next": _safe_next(next), "error": msg}, status)
            r.set_cookie(login_cookie, new_csrf, httponly=True, samesite="strict", secure=secure, max_age=1800,
                         path="/")
            if status == 429:
                r.headers["Retry-After"] = "900"
            return r

        if sec.rate_limited(svc.store, username, ip):
            return fail("Too many failed sign-in attempts. Try again in 15 minutes.", 429)
        r = svc.store.get_reviewer(username) if sec.valid_username(username) else None
        ok = sec.verify_password(password, r["password_hash"] if r else None) and bool(r and r["active"])
        svc.store.record_attempt([f"user:{username}", f"ip:{ip}"], ok)
        if not ok:
            return fail("Wrong username or password.", 401)
        raw, h, csrf = sec.new_session()
        svc.store.create_session(h, r["reviewer_id"], csrf)
        resp = RedirectResponse(_safe_next(next), status_code=303)
        resp.set_cookie(cookie, raw, httponly=True, samesite="strict", secure=secure, max_age=12 * 3600, path="/")
        resp.delete_cookie(login_cookie, path="/")
        return resp

    @app.post("/logout")
    def logout(user: dict = Depends(form_user), csrf_token: str = Form(max_length=128)):
        check_csrf(user, csrf_token)
        svc.store.revoke_session(user["session_hash"])
        resp = RedirectResponse("/login", status_code=303)
        resp.delete_cookie(cookie, path="/")
        return resp

    @app.get("/")
    def root(user: dict = Depends(page_user)):
        return RedirectResponse("/flags", status_code=303)

    # ------------------------------------------------------------------ flag queue
    def _filters(detector, severity, status, q, named):
        dets = sorted({f["detector_id"] for f in svc.wh.flags()})
        if detector and detector not in dets:
            raise HTTPException(422, "Unknown detector")
        if severity and severity not in SEVERITIES:
            raise HTTPException(422, "Unknown severity")
        if status and status not in wf.STATUSES + ["open", "stale"]:
            raise HTTPException(422, "Unknown status")
        if named and named not in ("yes", "no"):
            raise HTTPException(422, "named must be yes or no")
        return dets

    @app.get("/flags", response_class=HTMLResponse)
    def queue(request: Request, user: dict = Depends(page_user), detector: str = "", severity: str = "",
              status: str = "", q: str = "", named: str = "", page: int = 1):
        q = q[:100]
        dets = _filters(detector, severity, status, q, named)
        flags = svc.list_flags(detector or None, severity or None, status or None, q or None, named or None)
        page = max(1, min(page, 1000))
        ctx = {"flags": flags[(page - 1) * PAGE: page * PAGE], "total": len(flags), "page": page,
               "pages": max(1, -(-len(flags) // PAGE)), "detectors": dets, "severities": SEVERITIES,
               "f": {"detector": detector, "severity": severity, "status": status, "q": q, "named": named},
               "counts": _status_counts(svc.list_flags())}
        name = "_flag_rows.html" if request.headers.get("hx-request") else "flags.html"
        return render(request, name, ctx, user=user)

    @app.get("/flags/{flag_id}", response_class=HTMLResponse)
    def flag_detail(request: Request, flag_id: str, user: dict = Depends(page_user), ok: int = 0):
        f = svc.get_flag(flag_id)
        if not f:
            raise HTTPException(404, "No such flag in the current build")
        return render(request, "flag.html", {"f": f, "ok": ok, "error": None, "form": {}}, user=user)

    @app.post("/flags/{flag_id}/decide")
    def decide(request: Request, flag_id: str, user: dict = Depends(form_user),
               decision: str = Form(max_length=20), reason: str = Form("", max_length=wf.REASON_MAX + 100),
               notes: str = Form("", max_length=wf.NOTES_MAX + 100), csrf_token: str = Form("", max_length=128)):
        check_csrf(user, csrf_token)
        reviewer = svc.store.get_reviewer_by_id(user["reviewer_id"])
        try:
            svc.decide(flag_id, reviewer, decision, reason, notes, "web")
        except wf.ReviewError as e:
            f = svc.get_flag(flag_id)
            if not f:
                raise HTTPException(404, "No such flag in the current build")
            return render(request, "flag.html", {"f": f, "ok": 0, "error": str(e),
                                                 "form": {"decision": decision, "reason": reason, "notes": notes}},
                          409 if isinstance(e, wf.FourEyesError) else 422, user=user)
        return RedirectResponse(f"/flags/{flag_id}?ok=1", status_code=303)

    # ------------------------------------------------------------------ coverage and entities
    @app.get("/coverage", response_class=HTMLResponse)
    def coverage(request: Request, user: dict = Depends(page_user), data_type: str = "core", province: str = "",
                 q: str = "", fye_from: int | None = None, fye_to: int | None = None):
        if data_type not in ["core", *DATA_TYPES]:
            raise HTTPException(422, "Unknown data type")
        provs = svc.wh.provinces()
        if province and province not in provs:
            raise HTTPException(422, "Unknown province")
        for y in (fye_from, fye_to):
            if y is not None and not 2000 <= y <= 2100:
                raise HTTPException(422, "Year out of range")
        q = q[:80]
        years, ents = svc.wh.coverage(data_type, province or None, q or None, fye_from, fye_to)
        ctx = {"years": years, "ents": ents, "provinces": provs, "all_years": svc.wh.years(),
               "summary": svc.wh.coverage_summary(data_type, ents), "types": ["core", *DATA_TYPES],
               "f": {"data_type": data_type, "province": province, "q": q, "fye_from": fye_from, "fye_to": fye_to}}
        name = "_coverage_grid.html" if request.headers.get("hx-request") else "coverage.html"
        return render(request, name, ctx, user=user)

    @app.get("/entity/{gov_body_id}", response_class=HTMLResponse)
    def entity(request: Request, gov_body_id: str, user: dict = Depends(page_user)):
        e = svc.wh.entity(gov_body_id)
        if not e:
            raise HTTPException(404, "No such entity")
        shas = [r.get("source_sha256") for _, rows in e["sections"] for r in rows]
        if e.get("source_sha256"):
            shas.append(e["source_sha256"])
        flags = svc.list_flags(gov_body_id=gov_body_id)
        return render(request, "entity.html", {"e": e, "flags": flags, "raw_files": svc.wh.raw_files(shas)},
                      user=user)

    @app.get("/lineage/{sha}", response_class=HTMLResponse)
    def lineage(request: Request, sha: str, user: dict = Depends(page_user)):
        r = svc.wh.lineage(sha)
        if not r:
            raise HTTPException(404, "No raw file with that checksum in the current build")
        return render(request, "lineage.html", {"r": r}, user=user)

    # ------------------------------------------------------------------ audit trail and export
    @app.get("/audit", response_class=HTMLResponse)
    def audit(request: Request, user: dict = Depends(page_user), reviewer: str = "", flag_id: str = ""):
        ds = svc.store.decisions()
        if reviewer:
            ds = [d for d in ds if d["reviewer_username"] == reviewer[:32]]
        if flag_id:
            ds = [d for d in ds if d["flag_id"] == flag_id[:16]]
        for d in ds:
            d["decided_label"] = sast_label(d["decided_at_utc"])
            d["title"] = json.loads(d["flag_snapshot"]).get("title")
        return render(request, "audit.html", {"ds": list(reversed(ds)), "chain": svc.store.verify_chain(),
                                              "f": {"reviewer": reviewer, "flag_id": flag_id}}, user=user)

    @app.get("/export/reviewed.{fmt}")
    def export(fmt: str, user: dict = Depends(page_user), include: str = ""):
        rows = svc.reviewed(include_unreviewed=include == "all")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        if fmt == "csv":
            return Response(to_csv(rows), media_type="text/csv; charset=utf-8",
                            headers={"Content-Disposition": f'attachment; filename="thusa-reviewed-{stamp}.csv"'})
        if fmt == "json":
            return JSONResponse(rows, headers={"Content-Disposition":
                                               f'attachment; filename="thusa-reviewed-{stamp}.json"'})
        raise HTTPException(404, "Use .csv or .json")

    # ------------------------------------------------------------------ JSON API (bearer token; for bots/scripts)
    @app.get("/api/flags")
    def api_flags(r: dict = Depends(api_user), detector: str = "", severity: str = "", status: str = "",
                  q: str = "", named: str = "", limit: int = 50, offset: int = 0):
        _filters(detector, severity, status, q, named)
        flags = svc.list_flags(detector or None, severity or None, status or None, q[:100] or None, named or None)
        limit, offset = max(1, min(limit, 500)), max(0, offset)
        return {"total": len(flags), "limit": limit, "offset": offset,
                "flags": [_flag_summary(f) for f in flags[offset: offset + limit]]}

    @app.get("/api/flags/{flag_id}")
    def api_flag(flag_id: str, r: dict = Depends(api_user)):
        f = svc.get_flag(flag_id)
        if not f:
            raise HTTPException(404, "No such flag in the current build")
        return _flag_full(f)

    @app.post("/api/flags/{flag_id}/decisions", status_code=201)
    def api_decide(flag_id: str, body: DecisionIn, r: dict = Depends(api_user)):
        try:
            rec = svc.decide(flag_id, r, body.decision, body.reason, body.notes, body.channel)
        except wf.FourEyesError as e:
            raise HTTPException(409, str(e))
        except wf.ReviewError as e:
            raise HTTPException(422, str(e))
        return _decision_out(rec)

    return app


def _safe_next(n: str | None) -> str:
    n = n or "/flags"
    return n if n.startswith("/") and not n.startswith("//") and "\\" not in n and len(n) < 512 else "/flags"


def _status_counts(flags: list[dict]) -> dict:
    out: dict[str, int] = {}
    for f in flags:
        out[f["status"]] = out.get(f["status"], 0) + 1
    out["stale"] = sum(1 for f in flags if f["evidence_changed"])
    return out


def _flag_summary(f: dict) -> dict:
    return {k: f.get(k) for k in ("flag_id", "detector_id", "severity", "score", "title", "gov_body_id", "body_name",
                                  "period_label", "names_supplier", "status", "evidence_changed", "confirmed_by",
                                  "n_decisions")}


def _decision_out(d: dict) -> dict:
    return {k: d.get(k) for k in ("decision_id", "flag_id", "reviewer_username", "decision", "prev_status",
                                  "new_status", "reason", "notes", "channel", "decided_at_sast", "evidence_hash",
                                  "record_hash")}


def _flag_full(f: dict) -> dict:
    out = _flag_summary(f)
    out.update({"explanation": f["explanation"], "evidence": f["evidence"], "detector_version": f["detector_version"],
                "evidence_hash": f["evidence_hash"],
                "four_eyes_required": bool(f["names_supplier"]),
                "match": f["matched"].get("match"),
                "matched_records": [{"title": t, "rows": rows} for t, rows in f["matched"]["tables"]],
                "decisions": [_decision_out(d) for d in f["decisions"]]})
    return json.loads(json.dumps(out, default=str))
