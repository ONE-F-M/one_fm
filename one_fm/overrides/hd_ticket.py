import frappe, requests, re, json
from frappe import _
from frappe.utils import getdate, now, get_fullname
from json import dumps
from httplib2 import Http
from frappe.desk.form.assign_to import get as get_assignments,add as add_assignment
from helpdesk.helpdesk.doctype.hd_ticket.hd_ticket import HDTicket
from one_fm.api.doc_events import get_employee_user_id
from one_fm.utils import response
from frappe.utils.password import get_decrypted_password
try:
    from one_bpmn.api import send_message as send_processa_message
except ImportError:
    send_processa_message = None

class HDTicketOverride(HDTicket):
    @property
    def default_open_status(self):
        # Tickets created from the support email inbox (incoming mail) should
        # start as Draft; all other tickets use the SLA/HD Settings default.
        # When Frappe creates a ticket from an inbound email, it populates the
        # `email_account` field (HD Ticket's recipient_account_field) before the
        # doc is validated, so its presence on a new ticket signals email origin.
        if self.is_new() and self.get("email_account"):
            return "Draft"

        return frappe.db.get_value(
            "HD Service Level Agreement",
            self.sla,
            "default_ticket_status",
        ) or frappe.db.get_single_value("HD Settings", "default_ticket_status")

    def validate(self):
        super().validate()
        self.validate_hd_ticket()

    def validate_hd_ticket(self):
        bug_buster = frappe.get_all("Bug Buster",{'docstatus':1,'from_date':['<=',getdate()],'to_date':['>=',getdate()]},['employee'])
        if bug_buster:
            emp_user = frappe.get_value("Employee",bug_buster[0].employee,'user_id')
            if emp_user:
                self.custom_bug_buster = emp_user

        if (self.status == "Closed" or self.status == "Resolved") and not self.resolution_details:
            frappe.throw(_("Please fill in Resolution Details before closing the ticket."))

        if self.status == "Pending Deployment" and not self.resolution_details:
            frappe.throw(_("Please fill in Resolution Details before updating the status to Pending Deployment."))

    def on_update(self):
        super().on_update()
        self.apply_ticket_escalation()
        self.update_helpdesk_process_message()

    def apply_ticket_escalation(self):
        if self.agreement_status != 'Failed':
            return

        additional_settings = frappe.get_single("HD Additional Settings")
        escalation_priorities = [record.priority for record in additional_settings.escalation_priorities]
        escalation_ticket_types = [record.ticket_type for record in additional_settings.escalation_ticket_types]

        if self.priority not in escalation_priorities and self.ticket_type not in escalation_ticket_types:
            return

        # Fetch bug buster and his reports to details
        bug_buster = frappe.db.exists("Employee", {'user_id': self.custom_bug_buster})
        if not bug_buster:
            return

        bug_buster_reports_to_user_id = get_employee_user_id(frappe.db.get_value('Employee', bug_buster, 'reports_to'))

        # Fetch doc current assignments
        doc_assignments = [assignment.owner for assignment in get_assignments({'doctype': self.doctype, 'name': self.name})]

        # If reports to is not assigned then add assignment
        if bug_buster_reports_to_user_id not in doc_assignments:
            add_assignment({
                'assign_to': [bug_buster_reports_to_user_id],
                'doctype': self.doctype,
                'name': self.name,
                'description': _('HD Ticket {0} has been assigned to you due to escalation for failed SLA').format(self.name),
            })
    
    def update_helpdesk_process_message(self):
        if not send_processa_message:
            return
        previous_doc = self.get_doc_before_save()
        if not previous_doc:
            return
        message_name = False
        if self.has_value_changed("status") and previous_doc.status == "Resolved":
            if self.status == "Open":
                message_name = "hd_ticket_re_open"
            if self.status == "Closed":
                message_name = "hd_ticket_closed"
        if message_name:
            try:
                send_processa_message(
                    message_name=message_name,
                    context_doctype="HD Ticket",
                    context_docname=self.name
                )
            except Exception as e:
                frappe.log_error(message=frappe.get_traceback(), title="Processa Message Error (HD Ticket Raiser Review)")

    def after_insert(self):
        super().after_insert()
        self.send_google_chat_notification()

    def send_google_chat_notification(self):
        """Hangouts Chat incoming webhook to send the Issues Created, in Card Format."""
        # Fetch the Key and Token for the API
        try:
            default_api_integration = frappe.get_doc("Default API Integration")

            google_chat = frappe.get_doc("API Integration",
                [i for i in default_api_integration.integration_setting
                    if i.app_name=='Google Chat'][0].app_name)

            if google_chat.active:
                # Construct the request URL
                url = f"""{google_chat.url}/spaces/{google_chat.api_parameter[0].get_password('value')}/messages?key={google_chat.get_password('api_key')}&token={google_chat.get_password('api_token')}"""

                # Construct Message Body
                message = f"""<b>A new Issue has been created</b><br>
                    <i>Details:</i> <br>
                    Subject: {self.subject} <br>
                    Name: {self.name} <br>
                    Raised By (Email): {self.raised_by} <br>
                    Body: {self.description}<br>
                    """

                # Construct Card the allows Button action
                bot_message = {
                    "cards_v2": [
                        {
                        "card_id": "IssueCard",
                        "card": {
                        "sections": [
                        {
                            "widgets": [
                                {
                                "textParagraph": {
                                "text": message
                                }
                                },
                            {
                            "buttonList": {
                                "buttons": [
                                {
                                    "text": "Open Document",
                                    "onClick": {
                                    "openLink": {
                                        "url": frappe.utils.get_url(self.get_url()),
                                    }
                                    }
                                },
                                ]
                            }
                            }
                        ]
                        }
                        ]
                    }
                    }
                    ]
                }

                # Call the API
                message_headers = {'Content-Type': 'application/json; charset=UTF-8'}
                http_obj = Http()
                response = http_obj.request(
                    uri=url,
                    method='POST',
                    headers=message_headers,
                    body=dumps(bot_message),
                )
        except Exception as e:
             frappe.log_error(message=frappe.get_traceback(), title="Error while sending google notification")

    @property
    def get_name_for_mailing(self):
        try:
            employee_name = frappe.db.get_value("Employee", {"user_id": self.raised_by}, "employee_name")
            if employee_name:
                return employee_name
            return self.raised_by.split("@")[0]
        except (AttributeError, IndexError):
            return self.raised_by

    def on_communication_update(self, c):
        # If communication is incoming, then it is a reply from customer, and ticket must
        # be reopened.

        if not self.is_new() and c.sent_or_received == "Received" and self.status != "Draft":
            self.status = "Open"

        # If communication is outgoing, it must be a reply from agent
        if c.sent_or_received == "Sent":
            # Set first response date if not set already
            self.first_responded_on = (
                self.first_responded_on or frappe.utils.now_datetime()
            )

            if frappe.db.get_single_value("HD Settings", "auto_update_status"):
                self.status = "Replied"

        # Fetch description from communication if not set already. This might not be needed
        # anymore as a communication is created when a ticket is created.
        self.description = self.description or c.content
        self.flags.ignore_mandatory = True
        # Save the ticket, allowing for hooks to run.
        self.save()

@frappe.whitelist()
def create_dev_ticket(name, description):
    """
    Create a Jira bug ticket from HD Ticket
    """
    import base64
    from frappe.utils import get_url_to_form
    try:
        doc = frappe.get_doc("HD Ticket", name)
        doc_link = frappe.utils.get_url(get_url_to_form(doc.doctype, doc.name))

        # Use fallback if description is not provided
        description = cleanhtml(description) or doc.subject

        email = frappe.conf.get("jira_email")
        api_token = frappe.conf.get("jira_api_token")
        jira_url = frappe.conf.get("jira_url") or "https://one-fm.atlassian.net"
        project = frappe.conf.get("project_id")

        if not all([email, api_token, project]):
            frappe.throw("Jira credentials not found in site_config.json")

        # Prepare authentication
        auth = base64.b64encode(f"{email}:{api_token}".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json"
        }

        data = {
                    "fields": {
                        "project": {"key": project},
                        "summary": doc.subject,
                        "description": {
                            "type": "doc",
                            "version": 1,
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {"type": "text", "text": f"Link: {doc_link}"},
                                    ]
                                },
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {"type": "text", "text": f"Status: {doc.status}"},
                                    ]
                                },
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {"type": "text", "text": f"Priority: {doc.priority}"},
                                    ]
                                },
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {"type": "text", "text": f"Ticket Type: {doc.ticket_type}"},
                                    ]
                                },
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {"type": "text", "text": cleanhtml(description)},
                                    ]
                                },
                            ]
                        },
                        "issuetype": {"name": "Bug"}
                    }
                }


        url = f"{jira_url}/rest/api/3/issue"
        response = requests.post(url, headers=headers, json=data, timeout=10)


        # Safe JSON parsing
        try:
            resp_json = response.json()
        except Exception:
            resp_json = {}

        if response.status_code == 201:
            issue_key = resp_json.get("key")
            issue_url = f"{jira_url}/browse/{issue_key}"
            doc.db_set('custom_dev_ticket', issue_url)
            return {'status': 'success', 'jira_issue': issue_key}
        else:
            error_msg = resp_json.get("errors") or response.text
            return {'error': 'Dev Ticket Error', 'message': f"Dev ticket could not be created:\n{error_msg}"}

    except Exception as e:
        frappe.log_error(message=frappe.get_traceback(), title="Dev Ticket Creation Error")
        return {'error': 'Dev Ticket Error', 'message': f"Dev ticket could not be created:\n {str(e)}"}


CLEANER = re.compile('<.*?>')

def cleanhtml(raw_html):
  cleantext = re.sub(CLEANER, '', raw_html)
  return cleantext.replace("\t", "").replace("\n", "")



@frappe.whitelist()
def get_ticket_details(name: str):
    # Fetch the full document to get all custom fields
    try:
        ticket_doc = frappe.get_doc('HD Ticket', name)
    except frappe.DoesNotExistError:
        frappe.throw(_("Ticket not found"), frappe.DoesNotExistError)
    return {
        "message": "Operation Successful",
        "status_code": 200,
        "data": ticket_doc.as_dict(),  # Include full document to access all custom fields
    }

@frappe.whitelist()
def update_ticket(name: str, updates: str):
    """
    Method to update HD Ticket from the ticket edit page. This method will update the ticket with the provided updates and set the status to "Open".
    updates: JSON string with keys subject, description, type, priority, attachments, etc.
    """

    doc = frappe.get_doc("HD Ticket", name)
    try:
        updates_dict = json.loads(updates)
    except Exception:
        frappe.throw(_("Invalid updates JSON"))

    for field, value in updates_dict.items():
        setattr(doc, field, value)

    doc.status = "Open"

    doc.flags.ignore_mandatory = True
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    if send_processa_message:
        try:
            send_processa_message(
                message_name="hd_ticket_update",
                context_doctype="HD Ticket",
                context_docname=name
            )
        except Exception as e:
            frappe.log_error(message=frappe.get_traceback(), title="Processa Message Error (HD Ticket Update)")

    return {
        "message": "Operation Successful",
        "status_code": 201,
    }

@frappe.whitelist()
def get_priority():
    return _fetch_list("HD Ticket Priority")

@frappe.whitelist()
def get_process():
    return _fetch_list("Process")

@frappe.whitelist()
def create_github_issue(name, description):
    """
    Create a GitHub issue from an HD Ticket
    """
    try:
        doc = frappe.get_doc("HD Ticket", name)
        doc_link = frappe.utils.get_url(f"/app/hd-ticket/{doc.name}")

        # Use fallback if description is not provided
        description = cleanhtml(description) or doc.subject

        # Get GitHub credentials from site_config.json
        github_token = get_github_api_token(doc.custom_bug_buster)
        if not github_token:
            frappe.msgprint("GitHub token not found for user, please set it in your HD Agent profile")
            return {'error': 'GitHub Issue Error', 'message': "GitHub token not found for user, please set it in your HD Agent profile"}
        github_repo_owner = frappe.conf.get("github_repo_owner")
        github_repo_name = frappe.conf.get("github_repo_name")

        if not all([github_repo_owner, github_repo_name]):
            frappe.throw("GitHub credentials not found in site_config.json")

        headers = {
            "Authorization": f"token {github_token}",
            "Content-Type": "application/json"
        }

        data = {
            "title": doc.subject,
            "body": f"**From HD Ticket:** [{doc.name}]({doc_link})\n\n**Description:**\n{description}",
        }

        url = f"https://api.github.com/repos/{github_repo_owner}/{github_repo_name}/issues"
        response = requests.post(url, headers=headers, json=data, timeout=10)

        if response.status_code == 201:
            issue_url = response.json().get("html_url")
            doc.db_set('custom_github_issue_url', issue_url)
            return {'status': 'success', 'github_issue_url': issue_url}
        else:
            error_msg = response.json().get("message") or response.text
            frappe.log_error(message=f"GitHub Issue Creation Error: {error_msg}", title="GitHub Integration")
            return {'error': 'GitHub Issue Error', 'message': f"GitHub issue could not be created:\n{error_msg}"}

    except Exception as e:
        frappe.log_error(message=frappe.get_traceback(), title="GitHub Issue Creation Error")
        return {'error': 'GitHub Issue Error', 'message': f"GitHub issue could not be created:\n {str(e)}"}

@frappe.whitelist()
def update_ticket_with_feedback(ticket_id, feedback, action):
    try:
        if not ticket_id or not feedback or not action:
            return {
                "success": False,
                "message": "Missing required parameters"
            }
        
        ticket = frappe.get_doc("HD Ticket", ticket_id)
        user_name = get_fullname(frappe.session.user) or frappe.session.user
        current_time = now()
        
        if action == "close":
            ticket.feedback = feedback.strip()
            ticket.status = "Closed"
            ticket.add_comment("Comment", f"Ticket closed by {user_name}. Feedback: {feedback.strip()}")
            message = "Ticket has been closed successfully with your feedback."
            
        elif action == "reopen":
            current_description = ticket.description or ""
            feedback_section = f"\n\n--- Reopen Feedback ({current_time}) by {user_name} ---\n{feedback.strip()}"
            ticket.description = current_description + feedback_section
            ticket.status = "Open"
            ticket.add_comment("Comment", f"Ticket reopened by {user_name}. Reason: {feedback.strip()}")
            message = "Ticket has been reopened successfully. Your feedback has been added to the description."
            
        else:
            return {
                "success": False,
                "message": "Invalid action specified"
            }
        
        ticket.flags.ignore_mandatory = True
        ticket.save(ignore_permissions=True)
        frappe.db.commit()
        
        return {
            "success": True,
            "message": message
        }
        
    except Exception as e:
        frappe.log_error(message=f"Error in update_ticket_with_feedback: {str(e)}", title="HD Ticket Feedback Update Error")
        return {
            "success": False,
            "message": "An error occurred while updating the ticket"
        }

def get_github_api_token(user=None):
    if not user:
        user = frappe.session.user
    agent_for_user = frappe.db.exists("HD Agent", {"user": user, "is_active": 1})
    if not agent_for_user:
        frappe.msgprint("No active HD Agent found for user")
        return None
    token = get_decrypted_password("HD Agent", agent_for_user, 'github_api_token', raise_exception=True)
    if not token:
        frappe.msgprint("No GitHub API token found for user, please set it in your HD Agent profile. Follow <a href='https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-fine-grained-personal-access-token'>this link</a> for more details")
        return None
    return token

@frappe.whitelist()
def create_process_change_request(hd_ticket_name):
    """Create a Process Change Request from an HD Ticket."""
    user_roles = frappe.get_roles()
    if "Business Analyst" not in user_roles and "Process Owner" not in user_roles:
        frappe.throw(
            _("You are not authorized to create a Process Change Request."),
            title=_("Permission Denied"),
        )

    # Duplication check — block if a PCR already exists for this ticket
    existing_pcr = frappe.db.exists("Process Change Request", {"hd_ticket": hd_ticket_name})
    if existing_pcr:
        pcr_url = frappe.utils.get_url_to_form("Process Change Request", existing_pcr)
        frappe.throw(
            _("Process Change Request already exists for this HD Ticket: <a href='{0}'>{1}</a>").format(
                pcr_url, existing_pcr
            ),
            title=_("Exists"),
        )

    hd_ticket = frappe.get_doc("HD Ticket", hd_ticket_name)

    # Validate ticket type allows PCR creation
    initiate_pcr = frappe.db.get_value(
        "HD Ticket Type", hd_ticket.ticket_type, "initiate_process_change_request"
    )
    if not initiate_pcr:
        frappe.throw(_("This ticket type does not allow Process Change Request creation."))

    pcr = frappe.new_doc("Process Change Request")
    pcr.process_name = hd_ticket.custom_process
    pcr.requirement_summary = hd_ticket.subject
    pcr.requirement_details = hd_ticket.description
    pcr.hd_ticket = hd_ticket.name
    pcr.request_date = frappe.utils.today()
    pcr.status = "Open"
    pcr.flags.ignore_mandatory = True
    pcr.save(ignore_permissions=True)
    return pcr.name

@frappe.whitelist()
def get_filtered_processes(doctype_name=None, is_doctype_related="No"):
    """
    Get filtered list of processes based on doctype selection
    
    Args:
        doctype_name: The doctype to filter processes by
        is_doctype_related: Whether the ticket is doctype related ("Yes" or "No")
    
    Returns:
        List of process names
    """
    if is_doctype_related == "Yes" and doctype_name:
        # Get processes that have this doctype in their process_doctypes child table
        processes = frappe.db.sql("""
            SELECT DISTINCT p.name
            FROM `tabProcess` p
            INNER JOIN `tabProcess Doctype` pd ON pd.parent = p.name
            WHERE pd.document_type = %s
            ORDER BY p.name
        """, (doctype_name,), as_dict=True)
        
        process_list = [p.name for p in processes]
        
        # If no processes found, return generic processes
        if not process_list:
            generic_processes = frappe.db.get_all(
                "Process",
                filters={"is_generic": 1},
                pluck="name",
                order_by="name"
            )
            return generic_processes
        
        return process_list
    else:
        # Return all processes if not doctype related
        all_processes = frappe.db.get_all(
            "Process",
            pluck="name",
            order_by="name"
        )
        return all_processes
