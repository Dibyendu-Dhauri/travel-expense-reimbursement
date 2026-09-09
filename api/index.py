from __future__ import annotations

import base64
import hashlib
import hmac
import json
from html import escape
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from reimbursement_calculator import compute_claim_summary, fill_travel_forms

app = FastAPI(title="Nortex Travel Expense Reimbursement")

DEFAULT_APPROVALS = {
    "manager": {"role": "Reporting Manager", "name": "Suresh Iyer", "decision": "Pending", "date": "", "remarks": "Awaiting review"},
    "hod": {"role": "Head of Department", "name": "Meera Krishnan", "decision": "Pending", "date": "", "remarks": "Awaiting reporting manager approval"},
    "finance": {"role": "Finance - verification", "name": "Ravi Menon", "decision": "Pending", "date": "", "remarks": "Awaiting HOD approval"},
    "payment": {"role": "Finance - payment released", "name": "Finance Shared Services", "decision": "Pending", "date": "", "remarks": "Awaiting finance verification"},
}

COOKIE_NAME = "nortex_approval_state"
COOKIE_SECRET = b"nortex-demo-approval-secret"

ROLE_ACCESS = {"manager": "manager", "hod": "hod", "finance": "finance", "payment": "payment"}


def _load_approvals(request: Request) -> dict:
    encoded = request.cookies.get(COOKIE_NAME, "")
    try:
        payload, signature = encoded.rsplit(".", 1)
        expected = hmac.new(COOKIE_SECRET, payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError
        stored = json.loads(base64.urlsafe_b64decode(payload.encode()).decode())
        if set(stored) != set(DEFAULT_APPROVALS):
            raise ValueError
        return stored
    except (ValueError, KeyError, json.JSONDecodeError, UnicodeDecodeError):
        return json.loads(json.dumps(DEFAULT_APPROVALS))


def _approval_cookie(approvals: dict) -> str:
    payload = base64.urlsafe_b64encode(json.dumps(approvals, separators=(",", ":")).encode()).decode()
    signature = hmac.new(COOKIE_SECRET, payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def _next_pending(approvals: dict) -> str | None:
    if any(item["decision"] == "Rejected" for item in approvals.values()):
        return None
    for key in ("manager", "hod", "finance", "payment"):
        if approvals[key]["decision"] == "Pending":
            return key
    return None


def _workflow_rows(approvals: dict) -> list[dict]:
    return [{"role": "Employee (submitted by)", "name": "Chaitanya Reddy", "decision": "Submitted", "date": "20-Jun-2026", "remarks": "Claim submitted within policy deadline", "state": "approved"}] + [{**item, "key": key, "state": "approved" if item["decision"] in {"Approved", "Verified", "Released"} else "pending"} for key, item in approvals.items()]


def _approval_items(approvals: dict) -> list[dict]:
    return [approvals[key] for key in ("manager", "hod", "finance", "payment")]


def _money(value: float) -> str:
    return f"INR {value:,.2f}"


def _layout(title: str, active: str, content: str) -> str:
    nav_items = [("overview", "Overview", "/"), ("expenses", "Expenses", "/expenses"), ("approvals", "Approvals", "/approvals"), ("evidence", "Evidence", "/evidence")]
    nav = "".join(f'<a class="nav-link {"active" if active == key else ""}" href="{href}">{label}</a>' for key, label, href in nav_items)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{escape(title)} | Nortex</title>
<style>
:root{{--ink:#17231f;--muted:#68756f;--line:#dfe7e2;--paper:#f7f8f4;--white:#fff;--teal:#087f72;--teal-soft:#dff2ed;--amber:#a05b10;--amber-soft:#fff0d7;--red:#a43f31;--red-soft:#f9e4df}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}.shell{{min-height:100vh;display:grid;grid-template-columns:240px 1fr}}aside{{background:#163b35;color:#e9f4ee;padding:28px 20px}}.brand{{font-size:20px;font-weight:700;letter-spacing:.02em}}.brand small{{display:block;color:#a8c8bd;font-size:12px;font-weight:500;margin-top:3px}}.nav{{margin-top:48px;display:grid;gap:8px}}.nav-link{{color:#b8d1c8;text-decoration:none;padding:10px 12px;border-radius:7px}}.nav-link:hover,.nav-link.active{{background:#286359;color:#fff}}.side-note{{position:fixed;bottom:24px;width:195px;border-top:1px solid #427166;padding-top:14px;color:#a8c8bd;font-size:12px}}main{{padding:34px clamp(22px,5vw,70px);max-width:1320px;width:100%}}.top{{display:flex;justify-content:space-between;gap:20px;align-items:flex-start;margin-bottom:28px}}h1{{font-size:30px;line-height:1.1;margin:0 0 7px;letter-spacing:-.02em}}h2{{font-size:18px;margin:0 0 16px}}p{{margin:0;color:var(--muted)}}.eyebrow{{color:var(--teal);font-size:12px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;margin-bottom:8px}}.button{{display:inline-flex;align-items:center;gap:8px;background:var(--teal);color:white;padding:10px 14px;border-radius:6px;text-decoration:none;font-weight:650}}.button:hover{{background:#06665c}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:24px}}.card,.section{{background:var(--white);border:1px solid var(--line);border-radius:7px}}.card{{padding:20px}}.metric{{font-size:25px;font-weight:720;margin-top:6px}}.label{{color:var(--muted);font-size:12px}}.columns{{display:grid;grid-template-columns:1.25fr .75fr;gap:18px}}.section{{padding:22px;margin-bottom:18px}}.facts{{display:grid;grid-template-columns:repeat(2,1fr);gap:15px 28px}}.fact span{{display:block;color:var(--muted);font-size:12px}}.fact strong{{display:block;margin-top:2px}}table{{width:100%;border-collapse:collapse}}th{{text-align:left;color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.06em;padding:10px 9px;border-bottom:1px solid var(--line)}}td{{padding:12px 9px;border-bottom:1px solid #edf1ee;vertical-align:top}}tr:last-child td{{border-bottom:0}}.status{{display:inline-block;border-radius:999px;padding:4px 9px;font-size:12px;font-weight:700}}.approved,.verified{{color:var(--teal);background:var(--teal-soft)}}.pending{{color:var(--amber);background:var(--amber-soft)}}.note{{border-left:3px solid var(--amber);padding:9px 12px;margin:9px 0;background:#fffaf1;color:#69451d}}.muted{{color:var(--muted)}}.total{{display:flex;justify-content:space-between;padding:9px 0;border-bottom:1px solid var(--line)}}.total:last-child{{border-bottom:0;font-weight:750;font-size:17px}}@media(max-width:900px){{.shell{{grid-template-columns:1fr}}aside{{padding:18px}}.nav{{margin-top:20px;display:flex;overflow:auto}}.side-note{{display:none}}main{{padding:25px 18px}}.grid{{grid-template-columns:repeat(2,1fr)}}.columns{{grid-template-columns:1fr}}.top{{display:block}}.top .button{{margin-top:18px}}}}@media(max-width:540px){{.grid,.facts{{grid-template-columns:1fr}}table{{display:block;overflow-x:auto;white-space:nowrap}}h1{{font-size:26px}}}}
</style></head><body><div class="shell"><aside><div class="brand">NORTEX<small>Travel expense control</small></div><nav class="nav">{nav}</nav><div class="side-note">Sample trip workspace<br>NX-4471 · TRQ-2026-0000</div></aside><main>{content}</main></div></body></html>'''


def _summary() -> dict:
    return compute_claim_summary()


@app.get("/", response_class=HTMLResponse)
def overview() -> str:
    summary = _summary()
    findings = "".join(f'<div class="note">{escape(note)}</div>' for note in summary["policy_notes"])
    content = f'''<div class="top"><div><div class="eyebrow">Claim workspace</div><h1>Travel expense review</h1><p>One place to verify the trip, policy decision, and approval state.</p></div><a class="button" href="/download">↓ Download completed form</a></div><div class="grid"><div class="card"><div class="label">Net reimbursable claim</div><div class="metric">{_money(summary["reimbursable_total"])}</div></div><div class="card"><div class="label">Amount payable</div><div class="metric">{_money(summary["amount_payable"])}</div></div><div class="card"><div class="label">Disallowed expenses</div><div class="metric">{_money(summary["disallowed_total"])}</div></div><div class="card"><div class="label">Advance drawn</div><div class="metric">{_money(summary["approved_advance"])}</div></div></div><div class="columns"><section class="section"><h2>Claim overview</h2><div class="facts"><div class="fact"><span>Employee</span><strong>{escape(summary["employee_name"])} · {escape(summary["employee_code"])}</strong></div><div class="fact"><span>Travel request</span><strong>{escape(summary["travel_request_id"])}</strong></div><div class="fact"><span>Destination</span><strong>{escape(summary["city"])}</strong></div><div class="fact"><span>Travel dates</span><strong>{escape(summary["travel_dates"])}</strong></div><div class="fact"><span>Category</span><strong>{escape(summary["travel_category"])}</strong></div><div class="fact"><span>Purpose</span><strong>{escape(summary["purpose"])}</strong></div></div></section><section class="section"><h2>Settlement</h2><div class="total"><span>Employee-paid claim</span><strong>{_money(summary["reimbursable_total"])}</strong></div><div class="total"><span>Less: advance</span><strong>{_money(summary["approved_advance"])}</strong></div><div class="total"><span>Payable to employee</span><strong>{_money(summary["amount_payable"])}</strong></div><p class="muted" style="margin-top:14px">Policy checks completed against the supplied packet.</p></section></div><section class="section"><h2>Policy findings</h2>{findings}</section>'''
    return _layout("Overview", "overview", content)


@app.get("/expenses", response_class=HTMLResponse)
def expenses() -> str:
    summary = _summary()
    rows = "".join(f"<tr><td>{escape(row['date'])}<br><span class='muted'>{escape(row['time'])}</span></td><td>{escape(row['from'])}<br><span class='muted'>to {escape(row['to'])}</span></td><td>{escape(row['mode'])}</td><td>{escape(row['paid_by'])}</td><td><strong>{_money(row['amount'])}</strong></td><td class='muted'>{escape(row['proof_ref'])}</td></tr>" for row in summary["transport_records"])
    content = f"<div class='top'><div><div class='eyebrow'>Expense review</div><h1>Travel & transportation</h1><p>Extracted from the submitted email packet and matched to supporting evidence.</p></div><a class='button' href='/download'>↓ Download form</a></div><section class='section'><table><thead><tr><th>Date / time</th><th>Route</th><th>Mode</th><th>Paid by</th><th>Amount</th><th>Proof</th></tr></thead><tbody>{rows}</tbody></table></section><div class='columns'><section class='section'><h2>Lodging</h2><div class='facts'><div class='fact'><span>Hotel</span><strong>Keys Prime Hotel</strong></div><div class='fact'><span>Reimbursable</span><strong>{_money(summary['lodging_reimbursable'])}</strong></div><div class='fact'><span>Proof</span><strong>{escape(summary['hotel_invoice_ref'])}</strong></div><div class='fact'><span>Status</span><strong><span class='status approved'>Within policy</span></strong></div></div></section><section class='section'><h2>Disallowed</h2><div class='total'><span>Hotel extras + dinner</span><strong>{_money(summary['disallowed_total'])}</strong></div><p class='muted' style='margin-top:12px'>See policy findings on the overview for the reason codes.</p></section></div>"
    return _layout("Expenses", "expenses", content)


@app.get("/approvals", response_class=HTMLResponse)
def approvals(request: Request) -> str:
    approvals_state = _load_approvals(request)
    selected_role = request.query_params.get("role", "manager")
    selected_role = selected_role if selected_role in ROLE_ACCESS else "manager"
    rows = _workflow_rows(approvals_state)
    table = "".join(f"<tr><td>{i}</td><td><strong>{escape(row['role'])}</strong><br><span class='muted'>{escape(row['name'])}</span></td><td><span class='status {row['state']}'>{escape(row['decision'])}</span></td><td>{escape(row['date'] or '—')}</td><td class='muted'>{escape(row['remarks'])}</td></tr>" for i, row in enumerate(rows, 1))
    next_key = _next_pending(approvals_state)
    action = ""
    rejected = any(item["decision"] == "Rejected" for item in approvals_state.values())
    if rejected:
        action = "<section class='section'><h2>Claim rejected</h2><p><span class='status rejected'>Rejected</span> The workflow is stopped. The employee must correct and resubmit the claim.</p></section>"
    elif next_key:
        item = approvals_state[next_key]
        action = f"<section class='section'><h2>Reviewer action</h2><p><strong>{escape(item['role'])}</strong> · signed in as <strong>{escape(item['name'])}</strong></p><p class='muted' style='margin-top:8px'>{escape(item['remarks'])}</p><form method='post' action='/approvals/action?role={next_key}&decision=approve' style='display:inline'><button class='button' type='submit'>Approve / verify</button></form><form method='post' action='/approvals/action?role={next_key}&decision=reject' style='display:inline;margin-left:8px'><button class='button danger' type='submit'>Reject claim</button></form></section>"
    else:
        action = "<section class='section'><h2>Workflow complete</h2><p><span class='status approved'>Released</span> All approval stages are complete.</p></section>"
    content = f"<div class='top'><div><div class='eyebrow'>Workflow</div><h1>Approval & finance processing</h1><p>Each reviewer must take an action before the next stage becomes available.</p></div><a class='button' href='/download'>↓ Download form</a></div><section class='section'><p class='label'>Reviewer view</p><p style='margin-top:5px'><a href='/approvals?role=manager'>Manager</a> · <a href='/approvals?role=hod'>HOD</a> · <a href='/approvals?role=finance'>Finance</a> · <a href='/approvals?role=payment'>Payment</a></p></section><section class='section'><table><thead><tr><th>Level</th><th>Role / owner</th><th>Decision</th><th>Date</th><th>Remarks</th></tr></thead><tbody>{table}</tbody></table></section>{action}"
    return _layout("Approvals", "approvals", content)


@app.post("/approvals/action")
def approval_action(request: Request) -> RedirectResponse:
    approvals_state = _load_approvals(request)
    role = request.query_params.get("role", "")
    decision = request.query_params.get("decision", "")
    if role not in approvals_state or role != _next_pending(approvals_state) or decision not in {"approve", "reject"}:
        return RedirectResponse("/approvals", status_code=303)
    item = approvals_state[role]
    item["decision"] = "Approved" if decision == "approve" else "Rejected"
    item["date"] = "09-Sep-2026"
    item["remarks"] = "Approved after expense and evidence review" if decision == "approve" else "Rejected by assigned reviewer"
    if decision == "reject":
        for later in approvals_state.values():
            if later["decision"] == "Pending":
                later["remarks"] = "Blocked by rejected approval"
    response = RedirectResponse("/approvals", status_code=303)
    response.set_cookie(COOKIE_NAME, _approval_cookie(approvals_state), httponly=True, samesite="lax", secure=request.url.scheme == "https", max_age=60 * 60 * 24 * 30)
    return response


@app.get("/evidence", response_class=HTMLResponse)
def evidence() -> str:
    summary = _summary()
    rows = "".join(f"<tr><td>{i}</td><td><strong>{escape(ref)}</strong></td><td class='muted'>Parsed from sample inbox</td><td><span class='status verified'>Used</span></td></tr>" for i, ref in enumerate(summary["source_refs"],1))
    content = f"<div class='top'><div><div class='eyebrow'>Audit trail</div><h1>Evidence packet</h1><p>Source emails used to reconstruct this claim and populate the workbook.</p></div><a class='button' href='/download'>↓ Download form</a></div><section class='section'><table><thead><tr><th>#</th><th>Source file</th><th>Origin</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table></section><section class='section'><h2>Receipt images</h2><div class='facts'><div class='fact'><span>Hotel invoice</span><strong>{escape(summary["hotel_invoice_ref"])}</strong></div><div class='fact'><span>Dinner bill</span><strong>{escape(summary["dinner_ref"])}</strong></div></div><p class='muted' style='margin-top:16px'>The application reads MIME email bodies and uses OCR for available receipt images, with email text as a fallback.</p></section>"
    return _layout("Evidence", "evidence", content)


@app.get("/download")
def download(request: Request) -> Response:
    output = Path("/tmp/filled_travel_forms.xlsx")
    fill_travel_forms(output, approval_workflow=_approval_items(_load_approvals(request)))
    return Response(output.read_bytes(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=filled_travel_forms.xlsx"})
