import frappe, requests, re, json
from frappe import _
from frappe.utils import getdate, now, get_fullname
from json import dumps
from httplib2 import Http
from frappe.desk.form.assign_to import get as get_assignments,add as add_assignment
from helpdesk.helpdesk.doctype.hd_ticket.hd_ticket import HDTicket
from one_fm.processor import sendemail
from one_fm.api.doc_events import get_employee_user_id
from one_fm.utils import response
from frappe.utils.password import get_decrypted_password

class HDTicketOverride(HDTicket):
    def before_insert(self):
        self.set_im_mail_ticket_to_draft()

    def validate(self):
        super().validate()
        self.validate_hd_ticket()
        self.send_mail_for_completion()
        self.handle_process_based_on_doctype()

    def on_change(self):
        self.notify_issue_raiser_about_priority()

    def on_update(self):
        super().on_update()
        self.apply_ticket_escalation()
        self.notify_ticket_raiser_of_resolution_details()

    def after_insert(self):
        super().after_insert()
        self.send_google_chat_notification()
        if self.status ==  "Open":
            self.notify_ticket_raiser_of_receipt()

    def send_mail_for_completion(self):
        if self.is_new() and self.status == "Draft":
            subject = f"HelpDesk Ticket - {self.name}"
            context = dict(
                document_name=self.name,
                document_type=self.doctype,
                link_to_form=frappe.utils.get_url(f"/helpdesk/edit-ticket/{self.name}"),
                title=self.subject,
                header="Complete Ticket Details"
            )
            msg = frappe.render_template('one_fm/templates/emails/notify_issue_raiser_to_complete_ticket_details.html', context=context)
            frappe.enqueue(method=sendemail, queue="short", recipients=self.raised_by, subject=subject, content=msg, is_external_mail=True, is_scheduler_email=True)

    def set_im_mail_ticket_to_draft(self):
        if frappe.flags.in_receive or not self.via_customer_portal:
            self.status = "Draft"

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

    def handle_process_based_on_doctype(self):
        """Handle process field based on doctype selection"""
        if self.custom_is_doctype_related == "Yes" and self.custom_reference_doctype:
            # Get filtered processes for the selected doctype
            filtered_processes = get_filtered_processes(self.custom_reference_doctype, "Yes")
            
            # If doctype changed, check if current process is still valid
            if not self.is_new():
                previous_doc = self.get_doc_before_save()
                if previous_doc and previous_doc.custom_reference_doctype != self.custom_reference_doctype:
                    # Doctype changed, check if current process is still valid
                    if self.custom_process and self.custom_process not in filtered_processes:
                        self.custom_process = None
            
            # Auto-set process if only one match
            if len(filtered_processes) == 1 and not self.custom_process:
                self.custom_process = filtered_processes[0]

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

    def notify_ticket_raiser_of_resolution_details(self):
        if self.status == "Resolved":
            previous_doc = self.get_doc_before_save()
            if previous_doc and previous_doc.status != "Resolved":
                try:
                    subject = f"HD Ticket {self.name} Resolved"

                    args = frappe._dict({
                        "employee_name": self.get_name_for_mailing,
                        "ticket_subject": self.subject,
                        "resolution_details": self.resolution_details,
                        "base_url": frappe.utils.get_url(),
                        "doc_type": self.doctype,
                        "doc_name": self.name
                    })
                    message = frappe.render_template('one_fm/templates/emails/notify_ticket_raiser_of_resolution.html', context=args)
                    frappe.enqueue(method=sendemail, queue="short", recipients=self.raised_by, subject=subject, content=message, is_external_mail=True, is_scheduler_email=True)
                except Exception as e:
                    frappe.log_error(message=frappe.get_traceback(), title="HD Ticket")

    def notify_ticket_raiser_of_receipt(self):
        try:
            subject = f"HD Ticket {self.name} Raised"

            args = frappe._dict({
                "employee_name": self.get_name_for_mailing,
                "ticket_subject": self.subject,
                "base_url": frappe.utils.get_url(),
                "doc_type": self.doctype,
                "doc_name": self.name
            })
            message = frappe.render_template('one_fm/templates/emails/notify_ticket_raiser_receipt.html', context=args)
            frappe.enqueue(method=sendemail, queue="short", recipients=self.raised_by, subject=subject, content=message, is_external_mail=True, is_scheduler_email=True)
        except Exception as e:
            frappe.log_error(message=frappe.get_traceback(), title="HD Ticket")

    def notify_issue_raiser_about_priority(self):
        if self.ticket_type == "Bug":
            previous_doc = self.get_doc_before_save()
            if previous_doc:
                if any((previous_doc.priority != self.priority, previous_doc.ticket_type != self.ticket_type)):
                    status = "HotFix" if self.priority == "Urgent" else "BugFix"
                    is_hotfix = status == "HotFix"
                    title = f"Ticket {self.name} - {status}"
                    content_prefix = "A HotFix is in the works and should be completed within 24 hrs." if is_hotfix else "A BugFix is in the works and should be completed within a few days."
                    context = dict(
                        header="We understand the urgency, we are on it!" if is_hotfix else "It’s a bug and we’ll fix it!",
                        document_name=self.name,
                        document_type=self.doctype,
                        document_link=frappe.utils.get_url(self.get_url()),
                        content_prefix=content_prefix,
                        title=title,
                        priority=self.priority
                    )
                    msg = frappe.render_template('one_fm/templates/emails/notify_ticket_raiser_about_priority.html', context=context)
                    frappe.enqueue(method=sendemail, queue="short", recipients=self.raised_by, subject=title, content=msg, is_external_mail=True, is_scheduler_email=True)

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
        response = requests.post(url, headers=headers, json=data, timeout=5)

        if response.status_code == 201:
            issue_key = response.json().get("key")
            issue_url = f"{jira_url}/browse/{issue_key}"
            doc.db_set('custom_dev_ticket', issue_url)
            return {'status': 'success', 'jira_issue': issue_key}
        else:
            error_msg = response.json().get("errors") or response.text
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
    fields = ['subject', 'description', "priority", "custom_process"]
    hd_ticket = frappe.db.get_value('HD Ticket',{"name": name}, fields, as_dict=True)
    if not hd_ticket:
        frappe.throw(_("Ticket not found"), frappe.DoesNotExistError)
    return {
        "message": "Operation Successful",
        "status_code": 200,
        "data": hd_ticket,
    }

@frappe.whitelist()
def update_ticket(name: str, updates: str):
    """
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
    doc.notify_ticket_raiser_of_receipt()

    return {
        "message": "Operation Successful",
        "status_code": 201,
    }

def _fetch_list(doctype):
    try:
        data = frappe.db.get_list(doctype, pluck="name")
        return {
            "message": f"{doctype} fetched successfully",
            "status_code": 200,
            "data": data,
        }
    except Exception as e:
        frappe.log_error(message=frappe.get_traceback(), title=f"Error fetching list for {doctype}")
        return {
            "message": f"Failed to fetch {doctype}",
            "status_code": 500,
            "error": str(e),
        }

@frappe.whitelist()
def get_ticket_type():
    return _fetch_list("HD Ticket Type")

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
def create_pathfinder_log(hd_ticket_name):
    user_roles = frappe.get_roles()
    if "Business Analyst" not in user_roles and "Process Owner" not in user_roles:
        frappe.throw(_("You are not authorized to create a Pathfinder Log."), title=_("Permission Denied"))

    existing_log = frappe.db.exists("Pathfinder Log", {"hd_ticket": hd_ticket_name})
    if existing_log:
        log_url = frappe.utils.get_url_to_form("Pathfinder Log", existing_log)
        frappe.throw(
            _("Pathfinder Log already exists for this HD Ticket: <a href='{0}'>{1}</a>").format(
                log_url, existing_log
            ),
            title=_("Exists")
        )

    hd_ticket = frappe.get_doc("HD Ticket", hd_ticket_name)
    pathfinder_log = frappe.new_doc("Pathfinder Log")
    pathfinder_log.process_name = hd_ticket.custom_process
    pathfinder_log.goal_description = hd_ticket.description
    pathfinder_log.hd_ticket = hd_ticket.name
    pathfinder_log.flags.ignore_mandatory = True
    pathfinder_log.save(ignore_permissions=True)
    return pathfinder_log.name

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
