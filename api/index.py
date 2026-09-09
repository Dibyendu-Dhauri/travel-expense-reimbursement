from __future__ import annotations

from http.server import BaseHTTPRequestHandler
from io import BytesIO

from reimbursement_calculator import fill_travel_forms


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
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
