// Copyright (c) 2026, ONEFM and contributors
// For license information, please see license.txt

// WI-002400: the record offers exactly one of two buttons, decided by whether its PDF
// has reached Google Drive. Nothing is downloaded locally any more - the point of the
// story is that the file lives in the shared folder rather than on somebody's machine.
const POW_DRIVE_EVENT = "pow_drive_pdf";

frappe.ui.form.on("Proof of Work", {
	onload(frm) {
		// The upload happens in a background job, so the button has to change when the
		// job says so rather than when the click returns.
		if (!frm.__pow_drive_listener) {
			frm.__pow_drive_listener = true;
			frappe.realtime.on(POW_DRIVE_EVENT, (data) => {
				if (!data || data.name !== frm.doc.name) {
					return;
				}
				frm.doc.drive_file_id = data.drive_file_id;
				frm.refresh();
			});
		}
	},

	refresh(frm) {
		if (frm.is_new()) {
			return;
		}

		if (frm.doc.drive_file_id) {
			frm.add_custom_button(__("Open in Google Drive"), () => {
				window.open(pow_drive_file_link(frm.doc.drive_file_id), "_blank");
			});
			return;
		}

		frm.add_custom_button(__("Generate PDF"), () => generate_drive_pdf(frm));
	},
});

function pow_drive_file_link(file_id) {
	return `https://drive.google.com/file/d/${encodeURIComponent(file_id)}/view`;
}

function generate_drive_pdf(frm) {
	frappe.call({
		method: "one_fm.one_fm.doctype.proof_of_work.proof_of_work.generate_drive_pdf",
		args: { name: frm.doc.name },
		freeze: true,
		freeze_message: __("Sending this Proof of Work to Google Drive..."),
		callback: () => {
			// Queued, not done. The button stays as it is until the job reports back -
			// swapping it here would show "Open in Google Drive" for a file that may
			// never arrive.
			frappe.show_alert({
				message: __("Generating the PDF and uploading it to Google Drive."),
				indicator: "blue",
			});
		},
	});
}
