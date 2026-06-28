"""
Patch to remove the Employee marital_status property setter
This setter is no longer needed after standardizing marital status options across all modules
"""
import frappe


def execute():
    """
    Remove the property setter 'Employee-marital_status-options' that constrains
    the marital_status field options in the Employee DocType
    """
    
    # Delete the property setter if it exists
    if frappe.db.exists("Property Setter", "Employee-marital_status-options"):
        frappe.delete_doc("Property Setter", "Employee-marital_status-options")
        frappe.db.commit()
