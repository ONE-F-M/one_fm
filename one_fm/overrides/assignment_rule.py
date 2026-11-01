from one_fm.utils import get_doctype_mandatory_fields
from frappe.workflow.doctype.workflow_action.workflow_action import (

    get_workflow_name,
    get_confirm_workflow_action_url,
    get_doc_workflow_state
)

from one_fm.overrides.workflow import get_next_possible_transitions
from frappe.model.workflow import (
    apply_workflow,
    get_workflow_state_field
)
import frappe
from frappe.desk.form import assign_to

@frappe.whitelist()
def get_assignment_rule_description(doctype, doc=None):
    mandatory_fields, employee_fields, labels = get_doctype_mandatory_fields(doctype)
    message_html = '<p>Here is to inform you that the following {{ doctype }}({{ name }}) requires your attention/action.'
    if mandatory_fields:
        message_html += '''
        <br/>
        The details of the request are as follows:
        <br/>
        <table cellpadding="0" cellspacing="0" border="1" style="border-collapse: collapse;">
            <thead>
                <tr>
                    <th style="padding: 10px; text-align: left; background-color: #f2f2f2;">Label</th>
                    <th style="padding: 10px; text-align: left; background-color: #f2f2f2;">Value</th>
                </tr>
            </thead>
        <tbody>
        '''
        for mandatory_field in mandatory_fields:
            message_html += '''
            <tr>
                <td style="padding: 10px;">'''+labels[mandatory_field]+'''</td>
                <td style="padding: 10px;">{{'''+mandatory_field+'''}}</td>
            </tr>
            '''
        message_html += '</tbody></table>'
    message_html += '</p>'

    return message_html

def get_workflow_action_buttons(doc, user):
    """Generate the workflow action buttons HTML for a given document and user."""
    workflow = get_workflow_name(doc.get('doctype'))
    buttons_html = ""
    if workflow:
        transitions = get_next_possible_transitions(
            workflow, get_doc_workflow_state(doc), doc
        )
        action_details = [
            frappe._dict({
                "action_name": transition.action,
                "action_link": get_confirm_workflow_action_url(doc, transition.action, user),
            })
            for transition in transitions
        ]
        if action_details:
            buttons_html = "<div>"
            for action in action_details:
                buttons_html += '<a href={0} class="btn btn-primary btn-action" style="margin-right: 10px;">{1}</a>'.format(
                    action.action_link, action.action_name
                )
            buttons_html += "</div>"
    return buttons_html

def get_workflow_assignment_rule_description(doc, user):
    doctype = doc.get('doctype')
    message_html = get_assignment_rule_description(doctype)
    message_html += get_workflow_action_buttons(doc, user)
    return message_html

def do_assignment(self, doc):
    # clear existing assignment, to reassign
    if frappe.session.user == "Guest":
        frappe.set_user('Administrator')

    active_assignments = frappe.get_all(
        "ToDo",
        fields=["name", "allocated_to"],
        filters={"reference_type": doc.get("doctype"), "reference_name": doc.get("name"), "status": "Open", "assignment_rule": self.name},
        ignore_permissions=True,
    )
    for assignment in active_assignments:
        assign_to.set_status(
            doc.get("doctype"), 
            doc.get("name"), 
            todo=assignment.name, 
            assign_to=assignment.allocated_to, 
            status="Cancelled", 
            ignore_permissions=True
        )


    user = self.get_user(doc)

    if user:
        if self.is_assignment_rule_with_workflow:
            if self.description:
                # Use the assignment rule's stored description (supports Jinja ternary
                # expressions like {{ 'Arrival Time' if log_type == 'IN' else 'Leaving Time' }})
                # and append the dynamic workflow action buttons.
                description = self.description + get_workflow_action_buttons(doc, user)
            else:
                # Default: auto-generate the table from the doctype's mandatory fields.
                description = get_workflow_assignment_rule_description(doc, user)
        else:
            description = self.description

        # Newer Frappe v15 moved ignore_permissions from the whitelisted add() to _add();
        # older builds only have add(ignore_permissions=...).
        add_assignment = getattr(assign_to, "_add", assign_to.add)
        add_assignment(
            dict(
                assign_to=[user],
                doctype=doc.get("doctype"),
                name=doc.get("name"),
                description=frappe.render_template(description, doc),
                assignment_rule=self.name,
                notify=True,
                date=doc.get(self.due_date_based_on) if self.due_date_based_on else None,
            ),
            # As in core: the rule fires as whoever saved the document, who may not
            # have read access to it (e.g. a GR Operator completing a PACI).
            ignore_permissions=True,
        )

        # set for reference in round robin
        self.db_set("last_user", user)
        return True

    return False

def get_user_based_on_process_task(self):
    """
    Fetch the employee user assigned to process task
    """
    process_task_user = frappe.db.get_value('Process Task', { 'name': self.custom_routine_task }, 'employee_user')
    return process_task_user

def get_user(self, doc):
    """
	Get the next user for assignment
	"""
    if self.rule == "Round Robin":
        return self.get_user_round_robin()
    elif self.rule == "Load Balancing":
        return self.get_user_load_balancing()
    elif self.rule == "Based on Field":
        return self.get_user_based_on_field(doc)
    elif self.rule == "Based on Process Task":
        return self.get_user_based_on_process_task()
