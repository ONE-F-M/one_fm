from datetime import datetime
import frappe
from frappe import _
from one_fm.processor import sendemail


def due_purchase_order_payment_terms(is_scheduled_event=True):
    """
    Send notifications to Finance Office about due payment in terms
    for purchase order

    Args:
        is_scheduled_event -> Boolean (Default True) If method is triggered from anywhere else than the scheduled event, Pass "False" to avoid email trigger check from "ONEFM General Setting"
    """
    try:
        query = frappe.db.sql(f"""
            SELECT po.name as doc, po.supplier, po.supplier_name, pt.name, pt.payment_term,
            pt.due_date, pt.invoice_portion, pt.payment_amount, pt.outstanding
            FROM `tabPurchase Order` po JOIN `tabPayment Schedule` pt ON pt.parent=po.name
            WHERE pt.due_date='{datetime.today().date()}' AND
            po.docstatus=1 AND pt.parenttype='Purchase Order'
            ORDER BY po.name
        ;""", as_dict=1)

        if query:
            template = 'one_fm/tasks/erpnext/templates/due_purchase_order_payment_terms.html'
            content = frappe.render_template(
                template, {
                    'items':query,
                    'date':datetime.today(),
                    'total': sum([i.payment_amount for i in query]),
                    'company': frappe.utils.get_defaults('company')
                }
            )
            # get recipients
            recipients = [i.name for i in frappe.db.sql("""
                SELECT hr.parent, hr.role, u.name from `tabHas Role` hr INNER JOIN
                `tabUser` u ON hr.parent=u.name WHERE role LIKE 'Finance%'
                AND hr.parent LIKE '%@%' GROUP BY u.name;
            """, as_dict=1)]
            # send mail
            sendemail(
                recipients=recipients,
                subject="Due Purchase Order Payment",
                message=content, is_scheduler_email=is_scheduled_event)
    except Exception as e:
        frappe.log_error(str(e), 'Purchase Order payment schedule')
