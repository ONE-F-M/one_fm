"""
Patch to standardize marital status options across all modules
Maps old values to new standardized values:
- Unmarried -> Single
- Married -> Married
- Divorce -> Divorced
- Widow -> Widowed
- Unknown -> Single
"""
import frappe
from frappe.desk.reportview import get_count
from frappe.query_builder import DocType, Field
from frappe.query_builder.functions import Count


def execute():
    """
    Migrate marital status data from old options to new standardized options
    across Job Applicant, Onboard Employee, Work Permit, Transfer Paper, and PAM Visa
    using Query Builder for optimal performance
    """
    
    # Mapping of old values to new values
    marital_status_mapping = {
        "Unmarried": "Single",
        "Married": "Married",
        "Divorce": "Divorced",
        "Widow": "Widowed",
        "Unknown": "Single",
    }
    
    old_values = list(marital_status_mapping.keys())
    
    # Update Job Applicant marital status field using Query Builder
    JobApplicant = DocType("Job Applicant")
    
    for old_value, new_value in marital_status_mapping.items():
        if old_value != new_value:
            (
                frappe.qb.update(JobApplicant)
                .set(JobApplicant.one_fm_marital_status, new_value)
                .where(JobApplicant.one_fm_marital_status == old_value)
            ).run()
    
    # Update Onboard Employee marital status field using Query Builder
    OnboardEmployee = DocType("Onboard Employee")
    
    for old_value, new_value in marital_status_mapping.items():
        if old_value != new_value:
            (
                frappe.qb.update(OnboardEmployee)
                .set(OnboardEmployee.marital_status, new_value)
                .where(OnboardEmployee.marital_status == old_value)
            ).run()
    
    # Update Work Permit marital status field using Query Builder
    WorkPermit = DocType("Work Permit")
    
    for old_value, new_value in marital_status_mapping.items():
        if old_value != new_value:
            try:
                (
                    frappe.qb.update(WorkPermit)
                    .set(WorkPermit.marital_status, new_value)
                    .where(WorkPermit.marital_status == old_value)
                ).run()
            except Exception as e:
                frappe.log_error(f"Error updating Work Permit: {str(e)}")
    
    # Update Transfer Paper marital status field using Query Builder
    TransferPaper = DocType("Transfer Paper")
    
    for old_value, new_value in marital_status_mapping.items():
        if old_value != new_value:
            try:
                (
                    frappe.qb.update(TransferPaper)
                    .set(TransferPaper.marital_status, new_value)
                    .where(TransferPaper.marital_status == old_value)
                ).run()
            except Exception as e:
                frappe.log_error(f"Error updating Transfer Paper: {str(e)}")
    
    # Update PAM Visa marital status field using Query Builder
    PAMVisa = DocType("PAM Visa")
    
    for old_value, new_value in marital_status_mapping.items():
        if old_value != new_value:
            try:
                (
                    frappe.qb.update(PAMVisa)
                    .set(PAMVisa.marital_status, new_value)
                    .where(PAMVisa.marital_status == old_value)
                ).run()
            except Exception as e:
                frappe.log_error(f"Error updating PAM Visa: {str(e)}")
    
    # Update Visa Request marital status field using Query Builder
    VisaRequest = DocType("Visa Request")
    
    for old_value, new_value in marital_status_mapping.items():
        if old_value != new_value:
            try:
                (
                    frappe.qb.update(VisaRequest)
                    .set(VisaRequest.marital_status, new_value)
                    .where(VisaRequest.marital_status == old_value)
                ).run()
            except Exception as e:
                frappe.log_error(f"Error updating Visa Request: {str(e)}")
    
    frappe.db.commit()
