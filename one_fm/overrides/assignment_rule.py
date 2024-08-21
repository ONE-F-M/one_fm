from one_fm.utils import get_doctype_mandatory_fields
from frappe.workflow.doctype.workflow_action.workflow_action import (

    get_workflow_name,
    get_workflow_action_url,
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
def get_assignment_rule_description(doctype):
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

def get_workflow_assignment_rule_description(doc, user):
    doctype = doc.get('doctype')
    message_html = get_assignment_rule_description(doctype)
    workflow = get_workflow_name(doctype)
    if workflow:
        transitions = get_next_possible_transitions(
            workflow, get_doc_workflow_state(doc), doc
        )

        action_details = []

        for transition in transitions:
            action_details.append(
                frappe._dict(
                    {
                        "action_name": transition.action,
                        "action_link": get_workflow_action_url(transition.action, doc, user),
                    }
                )
            )

        if action_details and len(action_details) > 0:
            message_html += "<div>"
            for action in action_details:
                message_html += '<a href={0} class="btn btn-primary btn-action" style="margin-right: 10px;">{1}</a>'.format(action.action_link, action.action_name)
            message_html += "</div>"

    return message_html

def do_assignment(self, doc):
    # clear existing assignment, to reassign
    assign_to.clear(doc.get("doctype"), doc.get("name"))

    user = self.get_user(doc)

    if user:
        description = self.description
        if self.is_assignment_rule_with_workflow:
            description = get_workflow_assignment_rule_description(doc, user)
        assign_to.add(
            dict(
                assign_to=[user],
                doctype=doc.get("doctype"),
                name=doc.get("name"),
                description=frappe.render_template(description, doc),
                assignment_rule=self.name,
                notify=True,
                date=doc.get(self.due_date_based_on) if self.due_date_based_on else None,
            )
        )

        # set for reference in round robin
        self.db_set("last_user", user)
        return True

    return False
