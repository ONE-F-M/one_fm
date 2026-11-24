// Copyright (c) 2023, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Onboard Subcontract Employee", {
	refresh(frm) {
		if (
			frm.doc.docstatus === 0 &&
			frm.doc.provide_accommodation_by_company &&
			frm.doc.employee &&
			!frm.doc.accommodation_provided &&
			frappe.model.can_create("Accommodation Checkin Checkout")
		) {
			frm.add_custom_button(__("Accommodation Check-in"), () => {
				// The bed is picked on the check-in; Checked In on this record then links it.
				frappe.new_doc("Accommodation Checkin Checkout", {
					employee: frm.doc.employee,
					full_name: frm.doc.full_name,
					type: "IN",
					tenant_category: "Granted Service",
					new_or_current_resident: "New Resident",
					checkin_checkout_date_time: frappe.datetime.now_datetime(),
				});
			});
		}
	},
});
