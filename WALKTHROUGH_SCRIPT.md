# Web UI Walkthrough Script

Suggested length: 3 to 5 minutes. The accompanying `web_ui_walkthrough.mp4` is a concise visual cut of the same flow.

## 1. Opening

This application is a reviewer-facing web UI for Nortex's travel expense reimbursement workflow. It reads a trip's email packet and receipts, validates expenses against policy, exposes the approval status, and generates the official Excel settlement form.

## 2. Overview page

Open the hosted application and start on Overview. Point out the employee, travel request, destination, claim total, amount payable, disallowed expenses, advance, and policy findings. Explain that the page is a review workspace, not just a calculator output.

## 3. Expenses page

Open Expenses. Show the transport rows with date, route, paid-by status, amount, and proof reference. Explain that these rows come from discovered email records, not from fixed worksheet values. Point out lodging and disallowed expenses.

## 4. Evidence page

Open Evidence. Explain that the application parses `.eml` files with Python's standard `email` library, extracts MIME bodies and attachment names, and optionally uses OCR for receipt images. The source references make the claim auditable.

## 5. Approval page

Open Approvals. Show that the workflow starts pending. The Reporting Manager is the first available reviewer and sees `Approve / verify` and `Reject` actions. Approve the stage and refresh the page. Explain that the manager's action is now visible and the HOD stage is unlocked. Show the sequence: Manager, HOD, Finance verification, and Payment release. Rejecting a claim stops the chain and requests resubmission.

## 6. Downloaded workbook

Click Download completed form. Open the workbook and show the Travel Request Form, Expense Settlement Form, proof references, calculated totals, and approval rows. Explain that the workbook reflects the current approval state.

## 7. Close

The local CLI is also available with `python3 app.py`. The hosted demo is deliberately focused on the supplied sample packet. A production version would add authenticated users and durable database storage for approval actions.
