// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

// Once the process publishes, the Google Doc exists but the request that
// produced it offers no way to reach it — the requester has to go hunting in
// Drive for a file they asked the system to make.
//
// The button is added only when a link actually resolves, so it never appears
// and then fails. That costs one call on form refresh for requests that have
// reached a state where a document could exist; nothing is called for a
// request still waiting on approval.

const DOCUMENT_MAY_EXIST = ["Approved", "Published"];

frappe.ui.form.on("Document Request", {
	refresh(frm) {
		if (frm.is_new() || !DOCUMENT_MAY_EXIST.includes(frm.doc.status)) return;
		add_view_document_button(frm);
	},
});

function add_view_document_button(frm) {
	frappe.call({
		method:
			"one_fm.one_fm.doctype.document_request.document_request.get_published_document_link",
		args: { document_request: frm.doc.name },
		callback: (r) => {
			const link = r && r.message;
			if (!link || !link.url) {
				// Published with no reachable document is worth surfacing rather
				// than leaving the form looking normal — it means the run did not
				// record what it created.
				if (frm.doc.status === "Published") {
					frm.dashboard.add_comment(
						__("This document was published, but no Google Docs link was recorded for it."),
						"orange",
						true
					);
				}
				return;
			}

			frm.add_custom_button(__("View Document"), () => {
				window.open(link.url, "_blank", "noopener,noreferrer");
			}).addClass("btn-primary");

			frm.dashboard.add_comment(
				__("Published document: {0}", [
					`<a href="${frappe.utils.escape_html(link.url)}" target="_blank" rel="noopener noreferrer">${frappe.utils.escape_html(
						link.title || __("open in Google Docs")
					)}</a>`,
				]),
				"green",
				true
			);
		},
	});
}
