#  Travel Expense Reimbursement

This project automates the travel expense settlement process described in `PROBLEM_STATEMENT.md`. It reads the supplied employee record, policy, email packet, and receipt evidence; calculates the claim; validates expenses against the policy; and fills the official Excel travel request and settlement forms.

The implementation is intentionally a small, script-based application. The local workflow has no database, login flow, or frontend. Running `app.py` performs the complete workflow from extraction through workbook generation.

For hosted testing, the repository also includes a minimal Vercel function under `api/index.py`. This deployment surface is only an adapter around the existing calculator; the local CLI remains the primary workflow.

## Problem Solved

The input packet represents one employee's business trip. The application removes the manual work of:

- Reading travel approval and advance emails.
- Collecting flight, hotel, Uber, dinner, and return-transport amounts.
- Separating company-paid, employee-paid, reimbursable, and disallowed expenses.
- Applying the   travel policy.
- Transcribing the result into the official Excel forms.
- Recording the approval and finance-processing workflow in the output workbook.

## Project Inputs

| Path | Purpose |
| --- | --- |
| `sample_emails/` | The supplied `.eml` message packet for the trip. |
| `receipts/` | Image receipts attached to the hotel and dinner emails. |
| `employee_master.csv` | Employee master data. |
| `expense_policy.md` |   travel and expense policy. |
| `Travel_Expense_Forms_Template.xlsx` | Official travel request and settlement template. |

## How It Works

```text
Input packet
    -> Parse .eml files with Python email library
    -> Read email body and attachment metadata
    -> Run optional OCR on receipt images
    -> Extract labeled amounts from text
    -> Validate expenses against policy rules
    -> Calculate reimbursement and advance settlement
    -> Fill the official Excel workbook
```

### Email extraction

`reimbursement_calculator.py` uses Python's standard-library `email` package:

- `BytesParser` parses each `.eml` file.
- Plain-text and HTML body parts are collected.
- Subject and attachment filenames are available to the workflow.
- Regular expressions extract values such as `Total`, `GST`, `Grand total`, and `Invoice total`.

### Receipt image extraction

The two image receipts are supported through optional OCR:

- Pillow opens the image.
- `pytesseract` calls the Tesseract OCR engine.
- If OCR is unavailable or fails, the corresponding email body is used as a fallback.

The image files are:

- `receipts/hotel_invoice_1188.png`
- `receipts/dinner_bill_18jun.png`

### Policy validation

The Markdown policy is read as plain text with `pathlib`. The executable policy checks are implemented explicitly in `_validate_policy()` so the rules are deterministic and reviewable. The current workflow checks lodging, hotel extras, business entertainment, local transport, and company-paid flights.

## Installation

Use Python 3.10 or newer. From the project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

On macOS, install the Tesseract system executable to enable image OCR:

```bash
brew install tesseract
```

OCR is optional at runtime because the email text fallback keeps the workflow usable when Tesseract is not installed.

## Run

From the project directory:

```bash
python3 app.py
```

The script prints the claim summary and creates:

```text
filled_travel_forms.xlsx
```

The workbook is written directly to the project root and contains:

- Completed Travel Request Form.
- Completed Expense Settlement Form.
- Lodging, transport, and disallowed-expense rows.
- Reimbursement totals and advance settlement formulas.
- Employee submission, manager approval, HOD approval, finance verification, and payment-processing workflow.

## Expected Result For Supplied Packet

The current sample packet produces approximately:

```text
Reimbursable total: INR 22879.04
Amount payable:     INR 2879.04
Disallowed total:   INR 4205.00
```

The exact summary is also printed by `app.py` after each run.

## Vercel Deployment

Deploy from the project root with the Vercel CLI:

```bash
npx vercel login
npx vercel --prod
```

The deployed URL responds to `GET /api` with the calculated claim summary. Use `GET /api?download=1` to download a freshly generated `filled_travel_forms.xlsx` workbook.

Vercel's runtime filesystem is temporary, so the hosted function returns the workbook as a download and does not persist it between requests. Tesseract must also be available in the deployment environment for image OCR; otherwise the existing email-text fallback is used.

## Tests

Run the test suite with:

```bash
PYTHONPATH=. pytest -q
```

The tests cover the policy-based claim totals and successful workbook generation.

## Design Decisions And Assumptions

- The supplied packet describes one known employee and one known trip, so the current implementation uses the packet's specific message files and employee code `NX-4471`.
- Email and image values are held in memory as Python dictionaries and strings while the script runs. There is no database.
- The generated Excel workbook is the persistent output artifact.
- Flight and hotel booking costs marked as company-paid are excluded from the employee reimbursement calculation.
- Hotel extras and unsupported business entertainment are treated as disallowed expenses.
- The supplied email text is the fallback source when OCR dependencies or the Tesseract executable are unavailable.

## Deliberately Out Of Scope

This is a focused take-home implementation and does not currently include:

- Automatic scanning and classification of arbitrary email inboxes.
- Multiple employees or multiple trips in one run.
- A web interface or REST API.
- Database persistence, user accounts, or approval notifications.
- Cloud OCR or production document-management integration.
- Human review screens for ambiguous OCR results.

For production use, the next improvements would be subject/sender-based email classification, structured receipt extraction with confidence scores, duplicate detection, a review queue, and persistent audit records.
