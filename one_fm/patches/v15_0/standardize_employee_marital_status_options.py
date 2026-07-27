"""
Patch to standardize Employee marital status options
Maps old values to new standardized values:
- Unmarried -> Single
- Married -> Married
- Divorce -> Divorced
- Widow -> Widowed
- Unknown -> Single
"""
import frappe
from frappe.query_builder import DocType


def execute():
    """
    Migrate Employee marital status data from old options to new standardized
    options using Query Builder for optimal performance
    """

    # Mapping of old values to new values
    marital_status_mapping = {
        "Unmarried": "Single",
        "Married": "Married",
        "Divorce": "Divorced",
        "Widow": "Widowed",
        "Unknown": "Single",
    }

    # Update Employee marital status field using Query Builder
    Employee = DocType("Employee")

    for old_value, new_value in marital_status_mapping.items():
        if old_value != new_value:
            try:
                (
                    frappe.qb.update(Employee)
                    .set(Employee.marital_status, new_value)
                    .where(Employee.marital_status == old_value)
                ).run()
            except Exception as e:
                frappe.log_error(f"Error updating Employee: {str(e)}")

    frappe.db.commit()
