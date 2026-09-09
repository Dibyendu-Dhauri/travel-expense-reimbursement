from __future__ import annotations

from pathlib import Path

from reimbursement_calculator import compute_claim_summary, fill_travel_forms


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    summary = compute_claim_summary()
    output_path = fill_travel_forms(base_dir / "filled_travel_forms.xlsx")

    print("Travel expense validation completed.")
    print(f"Employee: {summary['employee_name']} ({summary['employee_code']})")
    print(f"Travel request ID: {summary['travel_request_id']}")
    print(f"Reimbursable total: INR {summary['reimbursable_total']:.2f}")
    print(f"Amount payable: INR {summary['amount_payable']:.2f}")
    print(f"Disallowed total: INR {summary['disallowed_total']:.2f}")
    print(f"Generated workbook: {output_path}")

    if not Path(output_path).exists():
        raise FileNotFoundError(f"Expected workbook not created at {output_path}")


if __name__ == "__main__":
    main()
