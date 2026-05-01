// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Subcontract Staff Attendance", {
	refresh(frm) {
		if (frm.doc.workflow_state === "Approved" && !frm.doc.__islocal) {
			frm.add_custom_button(__("Generate Purchase Invoice"), function() {
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

	let top_headers = `<th rowspan="2" style="vertical-align: middle;">${__("Employee ID")}</th><th rowspan="2" style="vertical-align: middle;">${__("Employee Name")}</th>`;
	let bottom_headers = ``;
	let dates = [];
	for (let i = 0; i < days_in_range; i++) {
		let current_date = moment(from_date).add(i, 'days');
		let is_friday = current_date.day() === 5;
		let day_name = current_date.format("ddd");
		let display_date = current_date.format("D/M");
		dates.push({date: current_date, is_friday: is_friday, day_num: current_date.date()});
		
		top_headers += `<th class="${is_friday ? 'bg-light' : ''}" style="min-width: 40px; text-align: center;">${day_name}</th>`;
		bottom_headers += `<th class="${is_friday ? 'bg-light' : ''}" style="min-width: 40px; text-align: center;">${display_date}</th>`;
	}
	top_headers += `<th rowspan="2" style="text-align: center; vertical-align: middle;">${__("Working Days")}</th><th rowspan="2" style="text-align: center; vertical-align: middle;">${__("Days Off")}</th>`;

	let rows = "";
	(frm.doc.subcontractor_staff_attendance_item || []).forEach(row => {
		let cells = `<td>${row.employee_id || ""}</td><td>${row.employee_name || ""}</td>`;
		let working_total = 0;
		let days_off_total = 0;

		dates.forEach(d => {
			let val = row[`day_${d.day_num}`] || "";
			if (frm.doc.attendance_record_based_on === "Attendance Status") {
				val = status_map[val] || val;
				
				if (val === "P" || val === "WFH") {
					working_total += 1;
				} else if (val === "HD") {
					working_total += 0.5;
				} else if (val === "DO" || val === "CDO" || val === "H") {
					// NOTE: Included "H" (Holiday) as working day usually but user said "Total DO statuses"
					// We'll increment DO for "DO" and "CDO", for actual working total we stick to P/WFH/HD
				}
				
				if (val === "DO" || val === "CDO") {
					days_off_total += 1;
				}
			} else if (frm.doc.attendance_record_based_on === "Shift Hours") {
				let hr_val = row[`day_${d.day_num}_hour`];
				val = hr_val || "";
				if (val && parseFloat(val) > 0) {
					working_total += 1;
				}
				
				let status_for_do = row[`day_${d.day_num}`] || "";
				let status_val_mapped = status_map[status_for_do] || status_for_do;
				if (status_val_mapped === "DO" || status_val_mapped === "CDO") {
					days_off_total += 1;
				}
			}
			cells += `<td class="${d.is_friday ? 'bg-light' : ''}" style="text-align: center;">${val}</td>`;
		});
		
		// Append calculations
		cells += `<td style="text-align: center; font-weight: bold;">${working_total}</td>`;
		cells += `<td style="text-align: center; font-weight: bold;">${days_off_total}</td>`;
		rows += `<tr>${cells}</tr>`;
	});

	const table_html = `
		<div style="overflow-x: auto; max-height: 60vh;">
			<table class="table table-bordered table-sm" style="font-size: 11px; white-space: nowrap;">
				<thead class="bg-light">
					<tr>${top_headers}</tr>
					<tr>${bottom_headers}</tr>
				</thead>
				<tbody>
					${rows}
				</tbody>
			</table>
		</div>
	`;

	const dialog = new frappe.ui.Dialog({
		title: __("Attendance Preview"),
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
