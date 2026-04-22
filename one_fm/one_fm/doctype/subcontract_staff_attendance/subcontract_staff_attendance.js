// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Subcontract Staff Attendance", {
	refresh(frm) {
		if (frm.doc.workflow_state === "Approved" && !frm.doc.__islocal) {
			frm.add_custom_button(__("Generate Invoice"), function() {
				frappe.confirm(__("Are you sure you want to generate a Purchase Invoice?"), function() {
					frappe.call({
						method: "generate_invoice",
						doc: frm.doc,
						freeze: true,
						callback: function(r) {
							if (r.message) {
								frappe.msgprint({
									title: __('Success'),
									indicator: 'green',
									message: __('Purchase Invoice {0} created successfully.', [
										`<a href="/app/purchase-invoice/${r.message}">${r.message}</a>`
									])
								});
							}
						}
					});
				});
			}).addClass("btn-primary");
		}

		if (frm.doc.workflow_state !== "Cancelled") {
			frm.add_custom_button(__("Preview Attendance"), function() {
				show_attendance_preview(frm);
			});
		}
	},

	fetch_attendance_record: function(frm) {
		if (!frm.doc.subcontractor_name || !frm.doc.from_date || !frm.doc.to_date || !frm.doc.attendance_record_based_on) {
			frappe.msgprint(__("Please select Subcontractor Name, From Date, To Date and Attendance Record Based On."));
			return;
		}

		frm.call({
			method: "fetch_subcontractor_staff",
			doc: frm.doc,
			freeze: true,
			freeze_message: __("Fetching attendance records..."),
			callback: function(r) {
				frm.refresh_field("subcontractor_staff_attendance_item");
				frappe.msgprint({title: __("Success"), indicator: "green", message: __("Attendance records fetched successfully.")});
			}
		});
	}
});

function show_attendance_preview(frm) {
	if (!frm.doc.from_date || !frm.doc.to_date) {
		frappe.msgprint(__("Please ensure From Date and To Date are set."));
		return;
	}

	const from_date = moment(frm.doc.from_date);
	const to_date = moment(frm.doc.to_date);
	const days_in_range = to_date.diff(from_date, 'days') + 1;

	if (days_in_range > 31) {
		frappe.msgprint(__("Date range exceeds 31 days. Matrix view is limited to one month."));
		return;
	}

	const status_map = {
		"Present": "P",
		"Absent": "A",
		"On Leave": "L",
		"Half Day": "HD",
		"Work From Home": "WFH",
		"Day Off": "DO",
		"Client Day Off": "CDO",
		"Fingerprint Appointment": "FA",
		"Medical Appointment": "MA",
		"Holiday": "H",
		"On Hold": "OH"
	};

	let headers = `<th>${__("Employee ID")}</th><th>${__("Employee Name")}</th>`;
	let dates = [];
	for (let i = 0; i < days_in_range; i++) {
		let current_date = moment(from_date).add(i, 'days');
		let is_friday = current_date.day() === 5;
		let display_date = current_date.format("D.M");
		dates.push({date: current_date, is_friday: is_friday, day_num: current_date.date()});
		headers += `<th class="${is_friday ? 'bg-secondary text-white' : ''}" style="min-width: 40px; text-align: center;">${display_date}</th>`;
	}

	let rows = "";
	(frm.doc.subcontractor_staff_attendance_item || []).forEach(row => {
		let cells = `<td>${row.employee_id || ""}</td><td>${row.employee_name || ""}</td>`;
		dates.forEach(d => {
			let val = row[`day_${d.day_num}`] || "";
			if (frm.doc.attendance_record_based_on === "Attendance Status") {
				val = status_map[val] || val;
			} else if (frm.doc.attendance_record_based_on === "Shift Hours") {
				val = row[`day_${d.day_num}_hour`] || "";
			}
			cells += `<td class="${d.is_friday ? 'bg-light' : ''}" style="text-align: center;">${val}</td>`;
		});
		rows += `<tr>${cells}</tr>`;
	});

	const table_html = `
		<div style="overflow-x: auto; max-height: 60vh;">
			<table class="table table-bordered table-sm" style="font-size: 11px; white-space: nowrap;">
				<thead class="bg-light">
					<tr>${headers}</tr>
				</thead>
				<tbody>
					${rows}
				</tbody>
			</table>
		</div>
	`;

	const dialog = new frappe.ui.Dialog({
		title: __("Attendance Preview Matrix"),
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "matrix_html",
				options: table_html
			}
		],
		primary_action_label: __("Close"),
		primary_action: () => dialog.hide()
	});

	dialog.$wrapper.find('.modal-dialog').css('max-width', '95%');
	dialog.show();
}
