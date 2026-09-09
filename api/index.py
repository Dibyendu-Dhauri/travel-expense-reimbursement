from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler
from io import BytesIO
from urllib.parse import parse_qs, urlparse

from openpyxl import load_workbook

from reimbursement_calculator import compute_claim_summary, fill_travel_forms


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        query = parse_qs(urlparse(self.path).query)

        if query.get("download") == ["1"]:
            self._send_workbook()
            return

        payload = {
            "service": "Nortex Travel Expense Reimbursement",
            "status": "ok",
            "summary": compute_claim_summary(),
            "download": "/api?download=1",
        }
        self._send_json(payload)

    def _send_json(self, payload: dict) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_workbook(self) -> None:
        output = "/tmp/filled_travel_forms.xlsx"
        fill_travel_forms(output)
        workbook_bytes = BytesIO()
        with open(output, "rb") as workbook_file:
            workbook_bytes.write(workbook_file.read())
        body = workbook_bytes.getvalue()

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.send_header("Content-Disposition", "attachment; filename=filled_travel_forms.xlsx")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
