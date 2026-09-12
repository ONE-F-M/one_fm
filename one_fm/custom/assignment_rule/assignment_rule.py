import frappe
import json
import os
from one_fm.utils import get_json_file

def get_assignment_rule_json_file(file_name, app_name="one_fm"):
    """
    Load JSON data from a file in the 'assignment_rule' folder.
    Args:
        file_name (str): The name of the JSON file (must end with '.json').
    Returns:
        dict: The parsed JSON data.
    """
    folder = frappe.get_app_path(app_name, "custom", "assignment_rule")
    return get_json_file(file_name, folder)

def create_assignment_rule(assignment_rule:dict, process_task_name:str=None):
    """
    Create or update an Assignment Rule based on the provided dictionary.

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
        frappe.log_error(title="Invalid assignment rule data.")
        return

    if "name" not in assignment_rule:
        frappe.log_error(title="Missing required field: 'name'.")
        return

    assignment_rule_name = assignment_rule["name"]

    try:
        if process_task_name:
            assignment_rule["custom_routine_task"] = process_task_name
        if not frappe.db.exists("Assignment Rule", assignment_rule_name):
            frappe.get_doc(assignment_rule).insert(ignore_permissions=True)
        else:
            doc = frappe.get_doc("Assignment Rule", assignment_rule_name)
            doc.update(assignment_rule)
            doc.save()
    except Exception as e:
        frappe.log_error(
            title="Assignment Rule Save Error",
            message=f"Failed to create or update Assignment Rule '{assignment_rule_name}': {frappe.get_traceback()}"
        )

def delete_assignment_rule(assignment_rule:dict):
    """
    Delete an Assignment Rule based on the 'name' field in the dictionary.
    Args:
        assignment_rule (dict): Dictionary containing at least:
            - name (str): The name of the Assignment Rule to delete.
    Returns:
        None
    """
    if not assignment_rule or not isinstance(assignment_rule, dict):
        frappe.log_error(title="Invalid assignment rule data.")
        return

    name = assignment_rule.get("name")
    if not name:
        frappe.log_error(title="Missing 'name' in assignment rule.")
        return

    try:
        if frappe.db.exists("Assignment Rule", name):
            frappe.delete_doc("Assignment Rule", name, ignore_permissions=True)
    except Exception as e:
        frappe.log_error(
            title="Assignment Rule Deletion Error",
            message=f"Failed to delete Assignment Rule '{name}': {frappe.get_traceback()}"
        )
