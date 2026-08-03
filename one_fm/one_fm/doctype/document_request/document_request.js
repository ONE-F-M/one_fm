// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

// Once the process publishes, the Google Doc exists but the request that
// produced it offers no way to reach it — the requester has to go hunting in
// Drive for a file they asked the system to make.
//
// `document_link` holds the URL and renders as a clickable link on its own
// (Data + options URL). The button exists on top of that because a button in
// the header is found without reading the form.
//
// The normal path costs no server call: the field is already on the document.
// The call below only fires for a request that published before anything wrote
// the field, and it is what fills it in — so each such request pays once.

const DOCUMENT_MAY_EXIST = ["Approved", "Published"];

frappe.ui.form.on("Document Request", {
	refresh(frm) {
		if (frm.is_new()) return;

		if (frm.doc.document_link) {
			add_view_button(frm, frm.doc.document_link);
			return;
		}

		if (!DOCUMENT_MAY_EXIST.includes(frm.doc.status)) return;
		repair_missing_link(frm);
	},
});

function add_view_button(frm, url) {
	frm.add_custom_button(__("View Document"), () => {
		window.open(url, "_blank", "noopener,noreferrer");
	}).addClass("btn-primary");
}

function repair_missing_link(frm) {
	frappe.call({
		method:
			"one_fm.one_fm.doctype.document_request.document_request.get_published_document_link",
		args: { document_request: frm.doc.name },
		callback: (r) => {
			const link = r && r.message;
			if (link && link.url) {
				// The call stored it, so reload_doc makes the field itself appear
				// rather than leaving a button next to an empty field.
				frm.reload_doc();
				return;
			}
			// Published with nothing to open is worth saying out loud — it means
			// the run never recorded what it created.
			if (frm.doc.status === "Published") {
				frm.dashboard.add_comment(
					__("This document was published, but no Google Docs link was recorded for it."),
					"orange",
					true
				);
			}
		},
	});
}
