import frappe
from frappe import _
from frappe import enqueue



def daily():
    """
    List of all tasks to be executed daily
    """
    enqueue("one_fm.tasks.erpnext.purchase_order.due_purchase_order_payment_terms")
    enqueue("one_fm.tasks.erpnext.issue.daily_open")
    enqueue("one_fm.tasks.erpnext.job_opening.uncheck_publish_job_opening_on_valid_till")
    enqueue("one_fm.api.tasks.automatic_shift_assignment")
