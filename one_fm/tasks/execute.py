import frappe
from frappe import _
from frappe import enqueue



def daily():
    """
    List of all tasks to be executed daily
    """
    enqueue("one_fm.controllers.tasks.erpnext.purchase_order.due_purchase_order_payment_terms")
