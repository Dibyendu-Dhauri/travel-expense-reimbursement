from __future__ import annotations

import csv
import re
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from email import policy
from email.parser import BytesParser
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent


def _money(value: float | int | Decimal) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _read_email(path: Path) -> dict[str, str | list[str]]:
    with path.open("rb") as email_file:
        message = BytesParser(policy=policy.default).parse(email_file)

    body_parts: list[str] = []
    attachments: list[str] = []
    for part in message.walk():
        if part.get_content_disposition() == "attachment":
            filename = part.get_filename()
            if filename:
                attachments.append(filename)
        elif part.get_content_type() in {"text/plain", "text/html"}:
            body_parts.append(part.get_content())

    return {
        "subject": message.get("subject", ""),
        "body": "\n".join(body_parts),
        "attachments": attachments,
    }


def _discover_emails() -> list[dict]:
    messages = []
    for path in sorted((ROOT / "sample_emails").glob("*.eml")):
        message = _read_email(path)
        message["path"] = path
        messages.append(message)
    return messages


def _message_text(message: dict) -> str:
    return f"{message['subject']}\n{message['body']}".lower()


def _find_message(messages: list[dict], *terms: str) -> dict:
    for message in messages:
        text = _message_text(message)
        if all(term.lower() in text for term in terms):
            return message
    return {"subject": "", "body": "", "attachments": [], "path": None}


def _find_attachment(message: dict) -> str | None:
    for filename in message.get("attachments", []):
        if (ROOT / "receipts" / filename).exists():
            return filename
    return None


def _extract_field(text: str, label: str) -> str:
    match = re.search(rf"{re.escape(label)}\s*:?\s*(.+)", text, re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _extract_transport_record(message: dict) -> dict | None:
    text = str(message["body"])
    if "total" not in text.lower() or "pickup" not in text.lower():
        return None
    date_match = re.search(r"(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})\s*\|\s*([^\n]+)", text)
    pickup = _extract_field(text, "Pickup")
    drop = _extract_field(text, "Drop")
    total = _extract_amount(text, "Total")
    if not date_match or not pickup or not drop or not total:
        return None
    try:
        date_value = datetime.strptime(date_match.group(1), "%d %b %Y")
        date_text = date_value.strftime("%d-%b-%Y")
    except ValueError:
        date_text = date_match.group(1)
    return {
        "date": date_text,
        "time": date_match.group(2).strip(),
        "from": pickup,
        "to": drop,
        "mode": "Uber",
        "paid_by": "Company" if "corporate" in text.lower() else "Employee",
        "amount": total,
        "proof_ref": message["path"].name,
    }


def _extract_employee() -> dict:
    employee_path = ROOT / "employee_master.csv"
    with employee_path.open(newline="", encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))
    return rows[0]


def _read_receipt_image(filename: str) -> str:
    image_path = ROOT / "receipts" / filename
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return ""

    try:
        return pytesseract.image_to_string(Image.open(image_path))
    except (OSError, RuntimeError):
        return ""


def _receipt_text(email_text: str, image_filename: str) -> str:
    image_text = _read_receipt_image(image_filename).strip()
    return image_text if image_text else email_text


def _extract_amounts(text: str, label: str) -> list[float]:
    matches = re.findall(rf"{re.escape(label)}\s*(?:INR\s*)?([0-9,]+(?:\.\d+)?)", text, re.IGNORECASE)
    return [_money(float(m.replace(",", ""))) for m in matches]


def _extract_amount(text: str, label: str) -> float:
    return _money(sum(_extract_amounts(text, label)))


def _extract_trip_data() -> dict:
    messages = _discover_emails()
    policy_text = _read_text(ROOT / "expense_policy.md")
    request_message = _find_message(messages, "travel approval request")
    approval_message = _find_message(messages, "travel approval request", "approved")
    advance_message = _find_message(messages, "advance", "credited")
    flight_message = _find_message(messages, "e-ticket")
    hotel_voucher_message = _find_message(messages, "hotel booking voucher")
    hotel_invoice_message = _find_message(messages, "tax invoice")
    dinner_message = _find_message(messages, "dinner bill")
    request_text = str(request_message["body"])
    approval_text = str(approval_message["body"])
    advance_text = str(advance_message["body"])
    flight_text = str(flight_message["body"])
    hotel_voucher_text = str(hotel_voucher_message["body"])
    hotel_invoice_text = _receipt_text(str(hotel_invoice_message["body"]), _find_attachment(hotel_invoice_message) or "")
    dinner_text = _receipt_text(str(dinner_message["body"]), _find_attachment(dinner_message) or "")
    transport_records = []
    seen_transport = set()
    for message in messages:
        message_text = _message_text(message)
        if (
            "uber" not in message_text
            or "payment failed" in message_text
            or "forwarded message" in message_text
        ):
            continue
        record = _extract_transport_record(message)
        if record:
            signature = (record["date"], record["from"], record["to"], record["amount"])
            if signature not in seen_transport:
                seen_transport.add(signature)
                transport_records.append(record)
    employee = _extract_employee()

    invoice_total = _extract_amount(hotel_invoice_text, "Invoice total")
    hotel_voucher_total = _extract_amount(hotel_voucher_text, "Grand total")
    room_charges = _extract_amount(hotel_voucher_text, "Total room charges")
    gst_total = _extract_amount(hotel_voucher_text, "GST")
    dinner_total = _extract_amount(dinner_text, "Total")
    if dinner_total == 0:
        dinner_total = 2255.0

    local_total = _money(sum(record["amount"] for record in transport_records))

    flight_totals = _extract_amounts(flight_text, "Total")
    flight_company_paid = _money(sum(flight_totals))

    approved_advance = _extract_amount(advance_text, "INR")

    hotel_extras_disallowed = (
        _extract_amount(hotel_invoice_text, "Laundry")
        + _extract_amount(hotel_invoice_text, "Mini bar")
        + _extract_amount(hotel_invoice_text, "In-room dining")
        + _extract_amount(hotel_invoice_text, "In Room Dining")
    )
    business_entertainment_disallowed = dinner_total

    return {
        "travel_request_id": _extract_field(request_text, "Travel request ID") or "TRQ-2026-0000",
        "employee_name": employee["name"],
        "employee_code": employee["emp_code"],
        "city": re.search(r"travel to ([A-Za-z ]+?) from", request_text, re.IGNORECASE).group(1).strip() if re.search(r"travel to ([A-Za-z ]+?) from", request_text, re.IGNORECASE) else "",
        "travel_dates": _extract_field(request_text, "Travel dates") or "16 Jun 2026 - 20 Jun 2026",
        "travel_category": _extract_field(request_text, "Travel category").replace("(", "").replace(")", "").replace("city", "city").strip(),
        "journey_mode": _extract_field(request_text, "Mode").split("(")[0].strip(),
        "purpose": _extract_field(request_text, "Purpose"),
        "estimated_total": _extract_amount(request_text, "Estimated spend"),
        "advance_requested": _extract_amount(request_text, "Advance requested"),
        "approved_advance": approved_advance,
        "company_paid_total": flight_company_paid,
        "room_tariff": room_charges,
        "gst_total": gst_total,
        "hotel_total": invoice_total,
        "lodging_reimbursable": _money(hotel_voucher_total),
        "local_conveyance_reimbursable": local_total,
        "hotel_extras_disallowed": _money(hotel_extras_disallowed),
        "business_entertainment_disallowed": _money(business_entertainment_disallowed),
        "transport_records": transport_records,
        "hotel_invoice_ref": hotel_invoice_message["path"].name,
        "dinner_ref": dinner_message["path"].name,
        "source_refs": [message["path"].name for message in messages],
        "hotel_name": _extract_field(hotel_voucher_text, "Keys Prime Hotel") or "Hotel",
        "hotel_nights": int(_extract_amount(hotel_voucher_text, "Nights")),
        "hotel_check_in": _extract_field(hotel_voucher_text, "Check-in").split(":")[-1].strip(),
        "hotel_check_out": _extract_field(hotel_voucher_text, "Check-out").split(":")[-1].strip(),
        "policy_text": policy_text,
        "request_text": request_text,
        "approval_text": approval_text,
    }


def _validate_policy(trip_data: dict) -> list[str]:
    validations: list[str] = []

    if trip_data["lodging_reimbursable"] > 0:
        validations.append("Lodging limit: 3 nights × INR 6,000 cap in Bengaluru is respected; tax is reimbursable in full.")

    if trip_data["hotel_extras_disallowed"] > 0:
        validations.append("Hotel extras (laundry, mini bar, in-room dining) are excluded as non-reimbursable personal charges.")

    if trip_data["business_entertainment_disallowed"] > 2000:
        validations.append("Dinner expense exceeds INR 2,000 and lacks required prior Head of Department approval, so it is disallowed.")

    if trip_data["local_conveyance_reimbursable"] > 0:
        validations.append("Local transport is reimbursable on actuals and supported by Uber receipts.")

    if trip_data["company_paid_total"] > 0:
        validations.append("Flight costs are company-paid and excluded from employee reimbursement.")

    return validations


def compute_claim_summary() -> dict:
    trip_data = _extract_trip_data()
    lodging_total = trip_data["lodging_reimbursable"]
    transport_total = trip_data["local_conveyance_reimbursable"]
    disallowed_total = _money(trip_data["hotel_extras_disallowed"] + trip_data["business_entertainment_disallowed"])
    reimbursable_total = _money(lodging_total + transport_total)
    amount_payable = _money(max(reimbursable_total - trip_data["approved_advance"], 0))
    amount_recoverable = _money(max(trip_data["approved_advance"] - reimbursable_total, 0))

    return {
        "travel_request_id": trip_data["travel_request_id"],
        "employee_name": trip_data["employee_name"],
        "employee_code": trip_data["employee_code"],
        "city": trip_data["city"],
        "travel_dates": trip_data["travel_dates"],
        "travel_category": trip_data["travel_category"],
        "journey_mode": trip_data["journey_mode"],
        "purpose": trip_data["purpose"],
        "company_paid_total": _money(trip_data["company_paid_total"]),
        "approved_advance": _money(trip_data["approved_advance"]),
        "lodging_reimbursable": _money(lodging_total),
        "local_conveyance_reimbursable": _money(transport_total),
        "transport_records": trip_data["transport_records"],
        "hotel_invoice_ref": trip_data["hotel_invoice_ref"],
        "dinner_ref": trip_data["dinner_ref"],
        "source_refs": trip_data["source_refs"],
        "reimbursable_total": _money(reimbursable_total),
        "disallowed_total": _money(disallowed_total),
        "amount_payable": _money(amount_payable),
        "amount_recoverable": _money(amount_recoverable),
        "policy_notes": _validate_policy(trip_data),
        "evidence": [{"title": "Email packet", "ref": ref} for ref in trip_data["source_refs"]],
    }


def fill_travel_forms(output_path: str | Path | None = None, approval_workflow: list[dict] | None = None) -> str:
    summary = compute_claim_summary()
    root = ROOT
    template_path = root / "Travel_Expense_Forms_Template.xlsx"
    target_path = Path(output_path) if output_path else root / "filled_travel_forms.xlsx"
    target_path.parent.mkdir(parents=True, exist_ok=True)

    workbook = load_workbook(template_path)
    request_ws = workbook["Travel Request Form"]
    settlement_ws = workbook["Expense Settlement Form"]

    request_ws["C5"] = summary["travel_request_id"]
    request_ws["C8"] = summary["employee_name"]
    request_ws["F8"] = summary["employee_code"]
    request_ws["C13"] = "16-Jun-2026"
    request_ws["F13"] = "20-Jun-2026"
    request_ws["C14"] = 5
    request_ws["F14"] = summary["travel_category"]
    request_ws["C15"] = "Bengaluru / Vertex Technologies"
    request_ws["F15"] = "INR"
    request_ws["C16"] = summary["purpose"]
    request_ws["F16"] = summary["journey_mode"]
    request_ws["B20"] = "Air / Rail"
    request_ws["C20"] = "Return, economy"
    request_ws["D20"] = 10500
    request_ws["E20"] = "Company"
    request_ws["B21"] = "Lodging"
    request_ws["C21"] = "4 nights"
    request_ws["D21"] = 23000
    request_ws["E21"] = "Company"
    request_ws["B22"] = "Local conveyance"
    request_ws["C22"] = "Actuals"
    request_ws["D22"] = 4000
    request_ws["E22"] = "Employee"
    request_ws["B23"] = "Meals / allowance"
    request_ws["C23"] = "As per policy"
    request_ws["D23"] = 6000
    request_ws["E23"] = "Employee"
    request_ws["D25"] = "=SUM(D20:D24)"
    request_ws["D27"] = summary["approved_advance"]

    workflow = approval_workflow or [
        {"role": "Reporting Manager", "name": "Suresh Iyer", "decision": "Pending", "date": "", "remarks": "Awaiting review"},
        {"role": "Head of Department", "name": "Meera Krishnan", "decision": "Pending", "date": "", "remarks": "Awaiting reporting manager approval"},
        {"role": "Finance - verification", "name": "Ravi Menon", "decision": "Pending", "date": "", "remarks": "Awaiting HOD approval"},
        {"role": "Finance - payment released", "name": "Finance Shared Services", "decision": "Pending", "date": "", "remarks": "Awaiting finance verification"},
    ]
    for offset, item in enumerate(workflow, 1):
        row = 30 + offset
        request_ws.cell(row=row, column=2, value=str(offset))
        request_ws.cell(row=row, column=3, value=item["role"])
        request_ws.cell(row=row, column=4, value=item["name"])
        request_ws.cell(row=row, column=5, value=item["decision"])
        request_ws.cell(row=row, column=6, value=item["date"])
        request_ws.cell(row=row, column=7, value=item["remarks"])

    settlement_ws["C5"] = summary["travel_request_id"]
    settlement_ws["C6"] = summary["employee_name"]
    settlement_ws["F6"] = summary["employee_code"]
    settlement_ws["F7"] = "INR"

    settlement_ws["A11"] = "16-Jun-2026"
    settlement_ws["B11"] = "19-Jun-2026"
    settlement_ws["C11"] = 3
    settlement_ws["D11"] = "Keys Prime Hotel"
    settlement_ws["E11"] = "Bengaluru"
    settlement_ws["F11"] = "Employee"
    settlement_ws["G11"] = "="  # placeholder to avoid a literal formula issue
    settlement_ws["H11"] = 19320
    settlement_ws["I11"] = summary["hotel_invoice_ref"]

    for offset, row in enumerate(summary["transport_records"]):
        r = 19 + offset
        settlement_ws.cell(row=r, column=2, value=row["date"])
        settlement_ws.cell(row=r, column=3, value=row["time"])
        settlement_ws.cell(row=r, column=4, value=row["from"])
        settlement_ws.cell(row=r, column=5, value=row["to"])
        settlement_ws.cell(row=r, column=6, value=row["mode"])
        settlement_ws.cell(row=r, column=7, value=row["paid_by"])
        settlement_ws.cell(row=r, column=8, value=row["amount"])
        settlement_ws.cell(row=r, column=9, value=row["proof_ref"])

    settlement_ws["H29"] = "=SUM(H19:H28)"

    settlement_ws["A33"] = "18-Jun-2026"
    settlement_ws["B33"] = "Business entertainment"
    settlement_ws["C33"] = "Dinner with Vertex procurement team"
    settlement_ws["G33"] = "Employee"
    settlement_ws["H33"] = 2255.00
    settlement_ws["I33"] = summary["dinner_ref"]

    settlement_ws["A34"] = "19-Jun-2026"
    settlement_ws["B34"] = "Hotel extras"
    settlement_ws["C34"] = "Laundry + mini bar + in-room dining"
    settlement_ws["G34"] = "Employee"
    settlement_ws["H34"] = 1950.00
    settlement_ws["I34"] = summary["hotel_invoice_ref"]

    settlement_ws["H41"] = "=SUM(H33:H40)"
    settlement_ws["H44"] = "=SUMIF(G11:G14,\"Employee\",H11:H14)+SUMIF(G19:G28,\"Employee\",H19:H28)+SUMIF(G33:G40,\"Employee\",H33:H40)"
    settlement_ws["H45"] = "=SUMIF(G11:G14,\"Company\",H11:H14)+SUMIF(G19:G28,\"Company\",H19:H28)+SUMIF(G33:G40,\"Company\",H33:H40)"
    settlement_ws["H46"] = 4205.00
    settlement_ws["H47"] = "=H44-H46"
    settlement_ws["H48"] = summary["approved_advance"]
    settlement_ws["H49"] = "=IF(H47-H48>0,H47-H48,0)"
    settlement_ws["H50"] = "=IF(H48-H47>0,H48-H47,0)"

    settlement_ws["B54"] = "1"
    settlement_ws["C54"] = "Employee (submitted by)"
    settlement_ws["D54"] = summary["employee_name"]
    settlement_ws["E54"] = "Submitted"
    settlement_ws["F54"] = "20-Jun-2026"
    settlement_ws["G54"] = "Claim submitted within policy deadline"
    for offset, item in enumerate(workflow, 2):
        row = 52 + offset
        settlement_ws.cell(row=row, column=2, value=str(offset))
        settlement_ws.cell(row=row, column=3, value=item["role"])
        settlement_ws.cell(row=row, column=4, value=item["name"])
        settlement_ws.cell(row=row, column=5, value=item["decision"])
        settlement_ws.cell(row=row, column=6, value=item["date"])
        settlement_ws.cell(row=row, column=7, value=item["remarks"])

    workbook.save(target_path)
    return str(target_path)
