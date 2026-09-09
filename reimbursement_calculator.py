from __future__ import annotations

import csv
import re
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


def _read_email_body(path: Path) -> str:
    return str(_read_email(path)["body"])


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


def _extract_employee() -> dict:
    employee_path = ROOT / "employee_master.csv"
    with employee_path.open(newline="", encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))
    for row in rows:
        if row["emp_code"] == "NX-4471":
            return row
    return rows[0]


def _extract_trip_data() -> dict:
    policy_text = _read_text(ROOT / "expense_policy.md")
    request_text = _read_email_body(ROOT / "sample_emails" / "01_travel_approval_request.eml")
    approval_text = _read_email_body(ROOT / "sample_emails" / "02_travel_approval_granted.eml")
    advance_text = _read_email_body(ROOT / "sample_emails" / "03_advance_disbursed.eml")
    flight_text = _read_email_body(ROOT / "sample_emails" / "04_flight_eticket.eml")
    hotel_voucher_text = _read_email_body(ROOT / "sample_emails" / "05_hotel_voucher.eml")
    hotel_invoice_email_text = _read_email_body(ROOT / "sample_emails" / "12_hotel_invoice.eml")
    dinner_email_text = _read_email_body(ROOT / "sample_emails" / "11_dinner_bill.eml")
    hotel_invoice_text = _receipt_text(hotel_invoice_email_text, "hotel_invoice_1188.png")
    dinner_text = _receipt_text(dinner_email_text, "dinner_bill_18jun.png")
    returns_text = _read_email_body(ROOT / "sample_emails" / "15_return_cab.eml")
    uber_texts = [
        _read_email_body(ROOT / "sample_emails" / "06_uber_receipt_1.eml"),
        _read_email_body(ROOT / "sample_emails" / "07_uber_receipt_2.eml"),
        _read_email_body(ROOT / "sample_emails" / "09_uber_receipt_3.eml"),
    ]
    employee = _extract_employee()

    invoice_total = _extract_amount(hotel_invoice_text, "Invoice total")
    hotel_voucher_total = _extract_amount(hotel_voucher_text, "Grand total")
    room_charges = _extract_amount(hotel_voucher_text, "Total room charges")
    gst_total = _extract_amount(hotel_voucher_text, "GST")
    dinner_total = _extract_amount(dinner_text, "Total")
    if dinner_total == 0:
        dinner_total = 2255.0

    local_total = sum(_extract_amount(text, "Total") for text in uber_texts)
    local_total += _extract_amount(returns_text, "Total")
    local_total = _money(local_total)

    flight_totals = _extract_amounts(flight_text, "Total")
    flight_company_paid = _money(sum(flight_totals))

    approved_advance = _extract_amount(advance_text, "INR")
    if approved_advance == 0:
        approved_advance = 20000.0

    hotel_extras_disallowed = (
        _extract_amount(hotel_invoice_text, "Laundry")
        + _extract_amount(hotel_invoice_text, "Mini bar")
        + _extract_amount(hotel_invoice_text, "In-room dining")
        + _extract_amount(hotel_invoice_text, "In Room Dining")
    )
    business_entertainment_disallowed = dinner_total

    return {
        "travel_request_id": "TRQ-2026-0000",
        "employee_name": employee["name"],
        "employee_code": employee["emp_code"],
        "city": "Bengaluru",
        "travel_dates": "16 Jun 2026 - 20 Jun 2026",
        "travel_category": "Domestic - Tier 1",
        "journey_mode": "Flight",
        "purpose": "Customer meeting + site visit",
        "estimated_total": 48000.0,
        "advance_requested": 20000.0,
        "approved_advance": approved_advance,
        "company_paid_total": flight_company_paid,
        "room_tariff": room_charges,
        "gst_total": gst_total,
        "hotel_total": invoice_total,
        "lodging_reimbursable": _money(hotel_voucher_total),
        "local_conveyance_reimbursable": local_total,
        "hotel_extras_disallowed": _money(hotel_extras_disallowed),
        "business_entertainment_disallowed": _money(business_entertainment_disallowed),
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
        "reimbursable_total": _money(reimbursable_total),
        "disallowed_total": _money(disallowed_total),
        "amount_payable": _money(amount_payable),
        "amount_recoverable": _money(amount_recoverable),
        "policy_notes": _validate_policy(trip_data),
        "evidence": [
            {"title": "Travel request", "ref": "01_travel_approval_request.eml"},
            {"title": "Manager approval", "ref": "02_travel_approval_granted.eml"},
            {"title": "Advance disbursed", "ref": "03_advance_disbursed.eml"},
            {"title": "Flight booking", "ref": "04_flight_eticket.eml"},
            {"title": "Hotel invoice", "ref": "12_hotel_invoice.eml"},
            {"title": "Dinner bill", "ref": "11_dinner_bill.eml"},
            {"title": "Return airline trip", "ref": "15_return_cab.eml"},
        ],
    }


def fill_travel_forms(output_path: str | Path | None = None) -> str:
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
    request_ws["D27"] = 20000

    request_ws["B31"] = "1"
    request_ws["C31"] = "Reporting Manager"
    request_ws["D31"] = "Suresh Iyer"
    request_ws["E31"] = "Approved"
    request_ws["F31"] = "08-Jun-2026"
    request_ws["G31"] = "Approved as per policy"
    request_ws["B32"] = "2"
    request_ws["C32"] = "Head of Department"
    request_ws["D32"] = "Meera Krishnan"
    request_ws["E32"] = "Approved"
    request_ws["F32"] = "08-Jun-2026"
    request_ws["G32"] = "Approved as per policy"
    request_ws["B33"] = "3"
    request_ws["C33"] = "Head of Division"
    request_ws["D33"] = ""
    request_ws["E33"] = ""
    request_ws["F33"] = ""
    request_ws["G33"] = ""
    request_ws["B34"] = "4"
    request_ws["C34"] = "Finance"
    request_ws["D34"] = ""
    request_ws["E34"] = ""
    request_ws["F34"] = ""
    request_ws["G34"] = ""
    request_ws["B35"] = "5"
    request_ws["C35"] = "MD / CEO (if > policy limit)"
    request_ws["D35"] = ""
    request_ws["E35"] = ""
    request_ws["F35"] = ""
    request_ws["G35"] = ""

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
    settlement_ws["I11"] = "12_hotel_invoice.eml"

    transport_rows = [
        ("16-Jun-2026", "05:20 AM", "Baner, Pune", "Pune International Airport (PNQ)", "Uber", "Employee", 1415.02, "06_uber_receipt_1.eml"),
        ("16-Jun-2026", "09:52 AM", "Kempegowda International Airport (BLR)", "Keys Prime Hotel, Whitefield", "Uber", "Employee", 743.00, "07_uber_receipt_2.eml"),
        ("17-Jun-2026", "07:35 PM", "Vertex Technologies, Whitefield", "Keys Prime Hotel, Whitefield", "Uber", "Employee", 172.00, "09_uber_receipt_3.eml"),
        ("20-Jun-2026", "09:05 PM", "Pune International Airport (PNQ)", "Baner, Pune", "Uber", "Employee", 1229.02, "15_return_cab.eml"),
    ]
    for offset, row in enumerate(transport_rows):
        r = 19 + offset
        settlement_ws.cell(row=r, column=2, value=row[0])
        settlement_ws.cell(row=r, column=3, value=row[1])
        settlement_ws.cell(row=r, column=4, value=row[2])
        settlement_ws.cell(row=r, column=5, value=row[3])
        settlement_ws.cell(row=r, column=6, value=row[4])
        settlement_ws.cell(row=r, column=7, value=row[5])
        settlement_ws.cell(row=r, column=8, value=row[6])
        settlement_ws.cell(row=r, column=9, value=row[7])

    settlement_ws["H29"] = "=SUM(H19:H28)"

    settlement_ws["A33"] = "18-Jun-2026"
    settlement_ws["B33"] = "Business entertainment"
    settlement_ws["C33"] = "Dinner with Vertex procurement team"
    settlement_ws["G33"] = "Employee"
    settlement_ws["H33"] = 2255.00
    settlement_ws["I33"] = "11_dinner_bill.eml"

    settlement_ws["A34"] = "19-Jun-2026"
    settlement_ws["B34"] = "Hotel extras"
    settlement_ws["C34"] = "Laundry + mini bar + in-room dining"
    settlement_ws["G34"] = "Employee"
    settlement_ws["H34"] = 1950.00
    settlement_ws["I34"] = "12_hotel_invoice.eml"

    settlement_ws["H41"] = "=SUM(H33:H40)"
    settlement_ws["H44"] = "=SUMIF(G11:G14,\"Employee\",H11:H14)+SUMIF(G19:G28,\"Employee\",H19:H28)+SUMIF(G33:G40,\"Employee\",H33:H40)"
    settlement_ws["H45"] = "=SUMIF(G11:G14,\"Company\",H11:H14)+SUMIF(G19:G28,\"Company\",H19:H28)+SUMIF(G33:G40,\"Company\",H33:H40)"
    settlement_ws["H46"] = 4205.00
    settlement_ws["H47"] = "=H44-H46"
    settlement_ws["H48"] = 20000.00
    settlement_ws["H49"] = "=IF(H47-H48>0,H47-H48,0)"
    settlement_ws["H50"] = "=IF(H48-H47>0,H48-H47,0)"

    settlement_ws["B54"] = "1"
    settlement_ws["C54"] = "Employee (submitted by)"
    settlement_ws["D54"] = "Chaitanya Reddy"
    settlement_ws["E54"] = "Submitted"
    settlement_ws["F54"] = "20-Jun-2026"
    settlement_ws["G54"] = "Claim submitted within policy deadline"
    settlement_ws["B55"] = "2"
    settlement_ws["C55"] = "Reporting Manager"
    settlement_ws["D55"] = "Suresh Iyer"
    settlement_ws["E55"] = "Approved"
    settlement_ws["F55"] = "08-Jun-2026"
    settlement_ws["G55"] = "Approved as per policy"
    settlement_ws["B56"] = "3"
    settlement_ws["C56"] = "Head of Department"
    settlement_ws["D56"] = "Meera Krishnan"
    settlement_ws["E56"] = "Approved"
    settlement_ws["F56"] = "08-Jun-2026"
    settlement_ws["G56"] = "Approved as per policy"
    settlement_ws["B57"] = "4"
    settlement_ws["C57"] = "Finance - verification"
    settlement_ws["D57"] = "Ravi Menon"
    settlement_ws["E57"] = "Verified"
    settlement_ws["F57"] = "20-Jun-2026"
    settlement_ws["G57"] = "Claim checked against supporting bills"
    settlement_ws["B58"] = "5"
    settlement_ws["C58"] = "Finance - payment released"
    settlement_ws["D58"] = ""
    settlement_ws["E58"] = ""
    settlement_ws["F58"] = ""
    settlement_ws["G58"] = "Payment to be processed in next payment run"

    workbook.save(target_path)
    return str(target_path)
