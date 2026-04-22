// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Accommodation Leave Movement", {
	refresh: function(frm) {
		frm.set_df_property("employee", "read_only", frm.doc.leave_application ? 1 : 0);

		if (frm.doc.docstatus == 1 && frm.doc.type == "OUT" && !frm.doc.checked_out) {
			frm.add_custom_button(__("Create Check-In"), function() {
				frappe.model.with_doctype("Accommodation Leave Movement", function() {
					frappe.call({
						method: "one_fm.accommodation.doctype.accommodation_leave_movement.accommodation_leave_movement.make_checkin_from_checkout",
						args: {
							source_name: frm.doc.name
						},
						callback: function(r) {
							if (r.message) {
								var doc = frappe.model.sync(r.message)[0];
								frappe.set_route("Form", doc.doctype, doc.name);
							}
						}
					});
				});
			}, __("Create"));
		}
	},
	leave_application: function(frm) {
		frm.set_df_property("employee", "read_only", frm.doc.leave_application ? 1 : 0);
	},
	onload: function(frm) {
		if (frm.is_new()) {
			// Scenario A: Created from Leave Application (OUT)
			if (frm.doc.leave_application) {
				frm.set_value("type", "OUT");
				
				// Make type, employee, and leave_application read-only
				frm.set_df_property("type", "read_only", 1);
				frm.set_df_property("employee", "read_only", 1);
				frm.set_df_property("leave_application", "read_only", 1);
				
				// Populate bed details using the employee field
				if (frm.doc.employee) {
					frappe.call({
						method: "one_fm.accommodation.doctype.accommodation_leave_movement.accommodation_leave_movement.get_last_active_checkin",
						args: {
							employee: frm.doc.employee
						},
						callback: function(r) {
							if (r.message) {
								frm.set_value("bed", r.message.bed);
								frm.set_value("accommodation", r.message.accommodation);
								frm.set_value("floor", r.message.floor);
								frm.set_value("accommodation_unit", r.message.accommodation_unit);
								frm.set_value("accommodation_space", r.message.accommodation_space);
								
								// Set Bed Details to Read-Only as requested
								const bed_fields = ["accommodation", "floor", "accommodation_unit", "accommodation_space", "bed"];
								bed_fields.forEach(field => frm.set_df_property(field, "read_only", 1));
							}
						}
					});
				}
				
				// Set Tenant Details to Read-Only as requested
				const tenant_fields = ["full_name", "passport_number", "designation", "project", "nationality", "employee_id", "civil_id", "employment_type", "employee_status"];
				tenant_fields.forEach(field => frm.set_df_property(field, "read_only", 1));
			}

			// Scenario B: Created from Check-Out (IN)
			if (frm.doc.checkin_reference) {
				frm.set_value("type", "IN");

				// Make type, employee, and checkout reference read-only
				frm.set_df_property("type", "read_only", 1);
				frm.set_df_property("employee", "read_only", 1);
				frm.set_df_property("checkin_reference", "read_only", 1);

				// Set Bed Details to Read-Only as requested
				const bed_fields = ["accommodation", "floor", "accommodation_unit", "accommodation_space", "bed"];
				bed_fields.forEach(field => frm.set_df_property(field, "read_only", 1));

				// Set Tenant Details to Read-Only as requested
				const tenant_fields = ["full_name", "passport_number", "designation", "project", "nationality", "employee_id", "civil_id", "employment_type", "employee_status"];
				tenant_fields.forEach(field => frm.set_df_property(field, "read_only", 1));
			}
		}
	}
});
