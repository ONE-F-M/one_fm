// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Vehicle Handover Log", {
	vehicle: function (frm) {
		// Assigned Driver is fetch_if_empty, so neither the client nor the server
		// overwrites a value that is already set - which is what lets a dispatcher name
		// the custodian for a vehicle that has none on record. The cost is that changing
		// the vehicle would otherwise leave the previous vehicle's driver attached to this
		// handover, so the driver is re-pointed at the newly chosen vehicle here.
		if (!frm.doc.vehicle) {
			frm.set_value("assigned_driver", null);
			return;
		}

		frappe.db.get_value("Vehicle", frm.doc.vehicle, "employee").then((r) => {
			// Cleared rather than left stale when the vehicle has no permanent
			// custodian: Assigned Driver is mandatory, so the dispatcher is prompted to
			// name who is legally responsible for the keys.
			frm.set_value("assigned_driver", (r.message && r.message.employee) || null);
		});
	},
});
