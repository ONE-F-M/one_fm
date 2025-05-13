import frappe
import json
import os

import os
import json
import frappe

def get_assignment_rule(file_name):
    """
    Executes the creation of an assignment rule from a JSON file.

    Args:
        file_name (str): The name of the JSON file located in the 'assignment_rule' folder.

    Return:
        The json data
    Raises:
        frappe.throw: If the file is not a .json file or the file is not found.
    """
    data = {}
    folder = frappe.get_app_path('one_fm', 'custom', 'assignment_rule')

    if not file_name.endswith(".json"):
        frappe.throw('Only JSON files are allowed')

    file_path = os.path.join(folder, file_name)
    if os.path.isfile(file_path):
        with open(file_path, 'r') as f:
            data = json.load(f)
    else:
        frappe.throw(f"File not found: {file_path}")

    return data

def create_assignment_rule(assignment_rule:dict):
    '''
        Method used to create/update assignment_rule.
        Args:
            assignment_rule (dict): A dictionary representing the assignment rule data.
                - name (str): The name of the assignment_rule.
                - document_type (str): The document type associated with the assignment rule.
                - priority (int): To sate the assignment rule priority.
                - disabled (int): Whether the assignment rule is enabled (1) or disabled (0).
                - description (str): Discription in the assignment rule used to content in the email notification.
                - doctype (str): The internal document type associated with the workflow.
                - is_assignment_rule_with_workflow (int): Whether the assignment rule is showing workflow buttons in the notification (1) or not showing (0).
                - assign_condition (str): To eval the condition to assign the document
                - close_condition (str): To eval the condition to un-assign the document
                - rule (str): Selction rule
                - assignment_days (List): List of days to assign
        Returns:
            None
    '''
    if not frappe.db.exists("Assignment Rule", assignment_rule['name']):
        frappe.get_doc(assignment_rule).insert(ignore_permissions=True)
    else:
        assignment_rule_obj = frappe.get_doc("Assignment Rule", assignment_rule['name'])
        assignment_rule_obj.update(assignment_rule)
        assignment_rule_obj.save()

def delete_assignment_rule(assignment_rule:dict):
    '''
        Method used to delete assignment rule
        Args:
            assignment_rule (dict): A dictionary representing the assignment rule data.
                - name (str): The name of the assignment rule.
        Returns:
            None
    '''
    if 'name' in assignment_rule and frappe.db.exists("Assignment Rule", assignment_rule['name']):
        frappe.delete_doc('Assignment Rule', assignment_rule['name'], ignore_permissions=True)
