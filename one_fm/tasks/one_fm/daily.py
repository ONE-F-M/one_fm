from datetime import datetime
import frappe
import json
from frappe.utils import getdate, get_last_day, add_days, today
from frappe.utils.data import get_url_to_form
from frappe.desk.query_report import *
from one_fm.processor import sendemail


def generate_contracts_invoice():
    """
        Generate Sales Invoice for Contracts
    """
    try:
        dt = datetime
        contracts = frappe.get_list('Contracts', filters={
            'workflow_state': 'Active',
            # 'due_date':str(dt.today().date().day)
        })
        # generate
        for contract in contracts:
            contract_doc = frappe.get_doc("Contracts", contract.name)
            contract_due_date = contract_doc.due_date

            if str(contract_due_date).lower() == "end of month" and getdate() == get_last_day(getdate()):
                contract_doc.generate_sales_invoice()

            elif contract_due_date == str(dt.today().date().day):
                contract_doc.generate_sales_invoice()

    except Exception as e:
        frappe.log(str(e), "Contracts Invoice")


def roster_projection_view_task():
    """
        Generate ROSTER projection
    """
    from datetime import datetime
    dt = datetime
    report = frappe.get_doc("Report", 'Roster Projection View')
    background_enqueue_run(report.name,
                           filters=json.dumps(
                               {'month': dt.today().month, 'year': dt.today().year}), user='Administrator'
                           )


def notify_for_employee_docs_expiry():
    """
        Notify Onboarding officers about employee docs expiration

        - Work Permit
        - Residency
        - Civil ID
        - Passport
    """
    try:
        supervisor = frappe.db.get_single_value(
            'GRD Settings', 'default_grd_supervisor')
        operator = frappe.db.get_single_value(
            'GRD Settings', 'default_grd_operator')
        operator_pifss = frappe.db.get_single_value(
            'GRD Settings', 'default_grd_operator_pifss')

        recipients = list(set([supervisor, operator, operator_pifss]))

        target_expiry_date = add_days(today(), 30)

        work_permit_employees = frappe.get_all("Employee",
                                            filters=[
                                                ["work_permit_expiry_date",
                                                    "=", target_expiry_date],
                                            ],
                                            fields=["name", "employee_name",
                                                    "work_permit_expiry_date"]
                                            )
        residency_employees = frappe.get_all("Employee",
                                            filters=[
                                                ["residency_expiry_date",
                                                    "=", target_expiry_date],
                                            ],
                                            fields=["name", "employee_name",
                                                    "residency_expiry_date"]
                                            )
        civil_id_employees = frappe.get_all("Employee",
                                            filters=[
                                                ["civil_id_expiry_date",
                                                    "=", target_expiry_date],
                                            ],
                                            fields=["name", "employee_name",
                                                    "civil_id_expiry_date"]
                                            )
        passport_employees = frappe.get_all("Employee",
                                            filters=[
                                                ["valid_upto", "=", target_expiry_date],
                                            ],
                                            fields=[
                                                "name", "employee_name", "valid_upto"]
                                            )

        def send_notification(document_type, employees):
            for employee in employees:
                subject = f"Document Expiry - {employee['employee_name']}"
                header = f"{employee['employee_name']}'s {document_type} is about to expire."
                message = f"Dear Onboarding Officer,<br><br>The following employee's {document_type} is expiring on {target_expiry_date}:<br><br>Employee Name: {employee['employee_name']}<br>Employee ID: {employee['name']}<br><br>Kindly take the necessary action."

                for recipient in recipients:
                    notification_doc = frappe.get_doc({
                        "doctype": "Notification Log",
                        "subject": subject,
                        "email_content": message,
                        "document_type": "Employee",
                        "document_name": employee['name'],
                        "for_user": recipient,
                    })
                    notification_doc.insert(ignore_permissions=True)
                    frappe.db.commit()

                    doc_link = get_url_to_form(
                        notification_doc.document_type, notification_doc.document_name)

                    context = {
                        "body_content": notification_doc.subject,
                        "description": notification_doc.email_content,
                        "document_type": notification_doc.document_type,
                        "document_name": notification_doc.document_name,
                        "doc_link": doc_link,
                        "header": header
                    }

                    msg = frappe.render_template(
                        'one_fm/templates/emails/notification_log.html', context=context)

                    sendemail(recipients=[recipient], subject=subject, content=msg, is_scheduler_email=True)

        send_notification("Work Permit", work_permit_employees)
        send_notification("Residency", residency_employees)
        send_notification("Civil ID", civil_id_employees)
        send_notification("Passport", passport_employees)
    except Exception as e:
        frappe.log_error(str(e), 'Employee Docs Expiry')
