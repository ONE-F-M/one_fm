import frappe

ALERT_USER = "i.anware@one-fm.com"


def execute():
	if not frappe.db.exists("User", ALERT_USER):
		return
	if frappe.db.get_single_value("Transportation Settings", "shipment_alert_user"):
		return
	frappe.db.set_single_value("Transportation Settings", "shipment_alert_user", ALERT_USER)
