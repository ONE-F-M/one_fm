// Copyright (c) 2025, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Event Staff", {
	// Frontend replace warnings have been removed as backend handles roster overlap directly.
  
	client_event(frm) {
		if (frm.doc.client_event) {
			frappe.db.get_value("Client Event", frm.doc.client_event,
				["start_date", "end_date", "event_start_datetime", "event_end_datetime"],
				(r) => {
					if (r) {
						if (!frm.doc.start_date) frm.set_value("start_date", r.start_date);
						if (!frm.doc.end_date) frm.set_value("end_date", r.end_date);
						if (!frm.doc.start_datetime) frm.set_value("start_datetime", r.event_start_datetime);
						if (!frm.doc.end_datetime) frm.set_value("end_datetime", r.event_end_datetime);
					}
				}
			);
		}
	},
	end_date(frm) {
		if (frm.doc.end_date && frm.doc.end_datetime) {
			let time_part = frm.doc.end_datetime.split(" ")[1];
			if (time_part) {
				let new_end_datetime = frm.doc.end_date + " " + time_part;
				frm.set_value("end_datetime", new_end_datetime);
			}
		}
	},
});
