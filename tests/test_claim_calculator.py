from reimbursement_calculator import compute_claim_summary, fill_travel_forms


def test_compute_claim_summary_matches_policy_and_trip_data():
    summary = compute_claim_summary()

    assert summary["travel_request_id"] == "TRQ-2026-0000"
    assert summary["employee_name"] == "Chaitanya Reddy"
    assert summary["approved_advance"] == 20000.0
    assert summary["company_paid_total"] == 10556.0
    assert round(summary["reimbursable_total"], 2) == 22879.04
    assert round(summary["amount_payable"], 2) == 2879.04
    assert round(summary["disallowed_total"], 2) == 4205.0


def test_fill_travel_forms_creates_completed_template():
    output_path = fill_travel_forms("/tmp/filled_travel_forms.xlsx")
    assert output_path.endswith("filled_travel_forms.xlsx")
    assert "filled_travel_forms.xlsx" in output_path
