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

	onload(frm) {
		// The requester is captured in validate, which is too late to be seen: the
		// field is read-only, so a new request opens with the requester and the
		// whole approval chain blank — and Frappe hides empty read-only fields, so
		// the column is not merely empty, it is absent. Someone filing a request
		// has no way to tell that the system knows who they are, or who will be
		// asked to approve it.
		//
		// This fills it from the same lookup validate uses, so the form cannot show
		// one requester and then save another.
		if (frm.is_new() && !frm.doc.requester) show_requester(frm);
	},

	setup(frm) {
		// Three pickers over the same register, each filtered to the part of it
		// that its field actually means.
		//
		// A withdrawn document has nothing to revise and nothing left to
		// withdraw, and input material was never a controlled document in the
		// first place — neither should be offerable. The document type is
		// included because a revision keeps the document's own type: offering a
		// Policy while the request says SOP only leads to the mismatch the server
		// then refuses. The server refuses all of this in validate too; these
		// filters just save the user from finding out after typing the rest of
		// the request.
		frm.set_query("reference_document", () => {
			const filters = { lifecycle_state: "Active", is_input_material: 0 };
			if (frm.doc.document_type) filters.document_type = frm.doc.document_type;
			return { filters };
		});

		// The guideline says HOW to write the document, so only a Guideline can
		// be one. Pointing this at a finished Policy or SOP is how a request for
		// one subject comes back written about another.
		frm.set_query("source_guideline", () => ({
			filters: { lifecycle_state: "Active", document_type: "Guideline" },
		}));

	},

	request_action(frm) {
		// A document picked for one action may be an illegal choice for another,
		// and a stale link is worse than an empty field.
		if (frm.doc.request_action === "Create" && frm.doc.reference_document) {
			frm.set_value("reference_document", null);
		}
		if (frm.doc.request_action !== "Create" && frm.doc.source_guideline) {
			// An Update takes its shape from the document it is revising, which
			// already came from a guideline. Leaving a guideline attached implies
			// it will be applied, and it will not.
			frm.set_value("source_guideline", null);
		}
	},

	document_type(frm) {
		// The reference picker is filtered by type, so a type change can leave a
		// document selected that is now the wrong kind — and the server would
		// refuse the save with a mismatch the user did not knowingly create.
		if (frm.doc.reference_document) {
			frappe.db
				.get_value("Document Register", frm.doc.reference_document, "document_type")
				.then((r) => {
					const kind = r && r.message && r.message.document_type;
					if (kind && frm.doc.document_type && kind !== frm.doc.document_type) {
						frm.set_value("reference_document", null);
						frappe.show_alert({
							message: __("Cleared the selected document — it is a {0}, not a {1}.", [
								kind,
								frm.doc.document_type,
							]),
							indicator: "orange",
						});
					}
				});
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

function show_requester(frm) {
	frappe.call({
		method: "one_fm.one_fm.doctype.document_request.document_request.get_requester_defaults",
		callback: (r) => {
			const chain = (r && r.message) || {};
			if (!chain.requester) {
				// The save would throw this same thing. Saying it before the request
				// is written saves the requester typing all of it first.
				frm.dashboard.add_comment(
					__(
						"Your user account is not linked to an Employee record, so this request cannot record who is asking for the document. Ask HR to set the User ID on your employee record."
					),
					"red",
					true
				);
				return;
			}
			frm.set_value(chain);
		},
	});
}
