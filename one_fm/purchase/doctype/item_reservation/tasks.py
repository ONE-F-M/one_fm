# Copyright (c) 2021 Anthony Emmanuel and contributors
# For license information, please see license.txt

import frappe
from frappe import enqueue
from frappe.utils import today

def clear_reservations():
    """
        clear complete reservations whose to_date
        greater than today.
    """
    reservations = frappe.db.sql(f"""
        UPDATE `tabItem Reservation` SET status='Completed'
        WHERE status='Active' AND to_date < '{today()}'
    ;""")
    frappe.reload_doctype('Item Reservation')

def queue_reservation():
    enqueue("one_fm.purchase.doctype.item_reservation.tasks.clear_reservations")
