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
        Method to notify Onboarding officers about employee docs expiration
    """
    try:
        # Get the GRD Settings to make the recipients
        grd_settings = frappe.get_single('GRD Settings')
        recipients = list(
            set([
                grd_settings.default_grd_supervisor,
                grd_settings.default_grd_operator,
                grd_settings.default_grd_operator_pifss
            ])
        )

        send_employee_doc_expiry_notification(get_employees_by_expiry(), recipients)

    except Exception as e:
        frappe.log_error(str(e), 'Employee Docs Expiry')

def get_employees_by_expiry_doc():
    target_expiry_date = add_days(today(), 30)
    expiry_fields = [
        ("work_permit_expiry_date", "Work Permit"),
        ("residency_expiry_date", "Residency"),
        ("civil_id_expiry_date", "Civil ID"),
        ("valid_upto", "Passport")
    ]
    employees_by_expiry = {}
    for expiry_field, expiry_doc in expiry_fields:
        employees_by_expiry[expiry_doc] = frappe.get_all(
            "Employee",
            filters=[
                [expiry_field, "=", target_expiry_date],
                ["status", "in", ["Active", "Vacation"]]
            ],
            fields=["name", "employee_name", expiry_field]
        )
    return employees_by_expiry

def send_employee_doc_expiry_notification(employees_by_expiry, recipients):
    for expiring_doc in employees_by_expiry:
        for employee in employees_by_expiry[expiring_doc]:
            subject = f"Document Expiry - {employee['employee_name']}"
            header = f"{employee['employee_name']}'s {expiring_doc} is about to expire."
            message = f"Dear Onboarding Officer,<br><br>The following employee's {expiring_doc} is expiring on {target_expiry_date}:<br><br>Employee Name: {employee['employee_name']}<br>Employee ID: {employee['name']}<br><br>Kindly take the necessary action."
            doc_link = get_url_to_form("Employee", employee['name'])
            for recipient in recipients:
                create_employee_doc_expiry_notification_log(subject, message, employee['name'], recipient)
                context = {
                    "body_content": subject,
                    "description": message,
                    "document_type": "Employee",
                    "document_name": employee['name'],
                    "doc_link": doc_link,
                    "header": header
                }
                msg = frappe.render_template('one_fm/templates/emails/notification_log.html', context=context)
                sendemail(recipients=[recipient], subject=subject, content=msg, is_scheduler_email=True)

def create_employee_doc_expiry_notification_log(subject, message, employee_name, recipient):
    notification_doc = frappe.get_doc({
        "doctype": "Notification Log",
        "subject": subject,
        "email_content": message,
        "document_type": "Employee",
        "document_name": employee_name,
        "for_user": recipient,
    })
    notification_doc.insert(ignore_permissions=True)
    frappe.db.commit()
