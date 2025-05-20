import frappe
import json
import os
from one_fm.utils import get_json_file

def get_assignment_rule_json_file(file_name):
    """
    Get the workflow JSON file.
    Args:
        file_name (str): The name of the JSON file located in the 'assignment_rule' folder.
    Return:
        dict: The JSON data loaded from the file.
    """
    folder = frappe.get_app_path("one_fm", "custom", "assignment_rule")
    return get_json_file(file_name, folder)

def create_assignment_rule(assignment_rule:dict):
    """
    Create or update an Assignment Rule.

    Args:
        assignment_rule (dict): A dictionary representing the assignment rule data.
            - name (str): The name of the assignment rule.
            - document_type (str): The document type associated with the assignment rule.
            - priority (int): The priority of the assignment rule.
            - disabled (int): 1 if the rule is disabled, 0 otherwise.
            - description (str): Description for email notification.
            - doctype (str): Internal doctype (should be 'Assignment Rule').
            - is_assignment_rule_with_workflow (int): 1 to show workflow buttons in the notification.
            - assign_condition (str): Condition to assign the document.
            - close_condition (str): Condition to unassign the document.
            - rule (str): Selection rule.
            - assignment_days (list): List of days to assign.

    Returns:
        None
    """
    if not assignment_rule or not isinstance(assignment_rule, dict):
        frappe.error_log("Invalid assignment rule data.")
        return

    if "name" not in assignment_rule:
        frappe.error_log("Missing required field: 'name'.")
        return

    try:
        if not frappe.db.exists("Assignment Rule", assignment_rule["name"]):
            frappe.get_doc(assignment_rule).insert(ignore_permissions=True)
        else:
            doc = frappe.get_doc("Assignment Rule", assignment_rule["name"])
            doc.update(assignment_rule)
            doc.save()
    except Exception as e:
        frappe.error_log(f"Failed to create or update Assignment Rule '{assignment_rule['name']}': {str(e)}")

def delete_assignment_rule(assignment_rule:dict):
    """
    Delete an Assignment Rule.
    Args:
        assignment_rule (dict): A dictionary with at least the 'name' of the rule.
    Returns:
        None
    """
    if not assignment_rule or not isinstance(assignment_rule, dict):
        frappe.error_log("Invalid assignment rule data.")

    name = assignment_rule.get("name")
    if not name:
        frappe.error_log("Missing 'name' in assignment rule.")
        return

    try:
        if frappe.db.exists("Assignment Rule", name):
            frappe.delete_doc("Assignment Rule", name, ignore_permissions=True)
    except Exception as e:
        frappe.error_log(f"Failed to delete Assignment Rule '{name}': {str(e)}")
