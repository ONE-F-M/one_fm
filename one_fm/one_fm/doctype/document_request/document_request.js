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
//
// One link covers every revision: a new version overwrites the same Drive file,
// so the URL never goes stale. What *can* go stale is whether the document is
// still in use, which is why a withdrawn document is called out rather than
// quietly linked.

const DOCUMENT_MAY_EXIST = ["Approved", "Published", "Deleted"];

frappe.ui.form.on("Document Request", {
	refresh(frm) {
		if (frm.is_new()) return;

		if (frm.doc.document_link) {
			add_view_button(frm, frm.doc.document_link);
			describe_lifecycle(frm);
			return;
		}

		if (!DOCUMENT_MAY_EXIST.includes(frm.doc.status)) return;
		repair_missing_link(frm);
	},

	setup(frm) {
		// A withdrawn document has nothing to revise and nothing left to
		// withdraw, so it must not be offerable. The server refuses it in
		// validate too — this only saves the user from finding out after typing
		// the rest of the request.
		frm.set_query("reference_document", () => ({
			filters: { lifecycle_state: "Active" },
		}));
	},

	request_action(frm) {
		// The previously picked document may no longer be a legal choice for the
		// new action, and a stale link is worse than an empty field.
		if (frm.doc.request_action === "Create" && frm.doc.reference_document) {
			frm.set_value("reference_document", null);
		}
	},
});

function add_view_button(frm, url) {
	frm.add_custom_button(__("View Document"), () => {
		window.open(url, "_blank", "noopener,noreferrer");
	}).addClass("btn-primary");
}

function describe_lifecycle(frm) {
	// Only a completed withdrawal needs explaining; everything else is either
	// self-evident from the status or still in flight.
	if (frm.doc.status !== "Deleted") return;

	frm.dashboard.add_comment(
		__(
			"This document has been withdrawn from use. Nothing was deleted — the document, its content and all of its versions are kept, and its Drive sharing was revoked. A System Manager can reactivate it from the document itself."
		),
		"orange",
		true
	);
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
