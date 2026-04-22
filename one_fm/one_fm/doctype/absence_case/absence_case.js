frappe.ui.form.on("Absence Case", {
	refresh(frm) {
		set_leave_application_query(frm);
		setup_leave_extension_button(frm);
		setup_unpaid_leave_buttons(frm);
		setup_location_status_buttons(frm);
		setup_formal_hearing_button(frm);
	},

	validate(frm) {
		validate_formal_hearing_datetime(frm);
	},
	formal_hearing_start_datetime(frm) {
		validate_formal_hearing_datetime(frm);
	},
	formal_hearing_end_datetime(frm) {
		validate_formal_hearing_datetime(frm);
	},
	unpaid_leave_request_decision(frm) {
		setup_unpaid_leave_buttons(frm);
	}
});

function set_leave_application_query(frm) {
	frm.set_query("leave_application", function() {
		return {
			filters: {
				"employee": frm.doc.employee,
				"leave_type": "Annual Leave"
			}
		};
	});
}

function setup_leave_extension_button(frm) {
	if (frm.doc.docstatus === 1 && frm.doc.received_leave_extension_request === "Yes" && frm.doc.leave_application) {
		frm.add_custom_button(__("Leave Extension Request"), function() {
			frappe.new_doc("Leave Extension Request", {
				"employee": frm.doc.employee,
				"leave_application": frm.doc.leave_application
			});
		}, __("Create"));
	}
}

function setup_location_status_buttons(frm) {
	if (frm.doc.docstatus === 1 && frm.doc.location_status === "Outside Kuwait" && frm.doc.has_contact_been_made === 0) {
		if (frm.doc.retain_the_employee === 0) {
			frm.add_custom_button(__("Resignation by Law"), function() {
				frappe.new_doc("Employee Resignation", {
					"employee": frm.doc.employee
				});
			}, __("Create"));
		} else if (frm.doc.retain_the_employee === 1) {
			frm.add_custom_button(__("Leave Extension"), function() {
				frappe.new_doc("Leave Application", {
					"employee": frm.doc.employee
				});
			}, __("Create"));
			frm.add_custom_button(__("Unpaid Leave"), function() {
				frappe.new_doc("Leave Application", {
					"employee": frm.doc.employee,
					"leave_type": "Leave without Pay"
				});
			}, __("Create"));
		}
	}
}

function setup_unpaid_leave_buttons(frm) {
	frm.remove_custom_button(__("Unpaid Leave"), __("Create"));
	frm.remove_custom_button(__("Resignation by Law"), __("Create"));

	if (frm.doc.docstatus === 1 && flt(frm.doc.annual_leave_balance) === 0) {
		if (frm.doc.unpaid_leave_request_decision === "Approve") {
			frm.add_custom_button(__("Unpaid Leave"), function() {
				frappe.new_doc("Leave Application", {
					"employee": frm.doc.employee,
					"leave_type": "Leave without Pay"
				});
			}, __("Create"));
		} else if (frm.doc.unpaid_leave_request_decision === "Reject") {
			frm.add_custom_button(__("Resignation by Law"), function() {
				frappe.new_doc("Employee Resignation", {
					"employee": frm.doc.employee
				});
			}, __("Create"));
		}
	}
}

function validate_formal_hearing_datetime(frm) {
	if (frm.doc.formal_hearing_start_datetime) {
		let start = frappe.datetime.str_to_obj(frm.doc.formal_hearing_start_datetime);
		let now = frappe.datetime.now_datetime();

		// 24-hour notice validation
		let diff = (start - now) / 1000 / 3600; // difference in hours
		if (diff < 24) {
			let min_time = frappe.datetime.add_to_date(now, 0, 0, 1); // +24 hours
			let msg = __("Formal Hearing must be scheduled at least 24 hours in advance. <br><br> " +
						 "<b>Earliest possible time:</b> {0} <br>" +
						 "<b>Current notice:</b> {1} hours",
						 [frappe.datetime.format_datetime(min_time), Math.round(diff * 100) / 100]);

			frappe.msgprint({
				message: msg,
				indicator: "red",
				title: __("Notice Period Verification")
			});
			frappe.validated = false;
		}

		// End time validation
		if (frm.doc.formal_hearing_end_datetime) {
			let end = frappe.datetime.str_to_obj(frm.doc.formal_hearing_end_datetime);
			if (end <= start) {
				frappe.msgprint({
					message: __("Formal Hearing End Datetime must be after Start Datetime."),
					indicator: "red",
					title: __("Invalid Duration")
				});
				frappe.validated = false;
			}
		}
	}
}

function setup_formal_hearing_button(frm) {
	if (frm.doc.docstatus === 1 && frm.doc.location_status === "Inside Kuwait") {
		frm.add_custom_button(__("Formal Hearing"), function() {
			frappe.model.open_mapped_doc({
				method: "one_fm.one_fm.doctype.absence_case.absence_case.make_formal_hearing",
				frm: frm
			});
		}, __("Create"));
	}
}
