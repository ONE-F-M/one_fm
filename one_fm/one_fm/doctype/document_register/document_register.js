// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

// A withdrawn document looks identical to a live one on this form: nothing is
// deleted, the content is still there, and the Drive link still resolves. That
// is the intended design, and it is also the reason the state has to be said
// loudly — an approver reading a superseded procedure and acting on it is the
// failure this register exists to prevent.
//
// Reactivation lives here rather than behind a Document Request because
// withdrawing a document in error is a correction to the register, not a
// request to rewrite it.

frappe.ui.form.on("Document Register", {
	refresh(frm) {
		if (frm.is_new()) return;

		show_lifecycle_banner(frm);
		add_lifecycle_button(frm);
		add_open_button(frm);
		show_version_history(frm);
	},
});

function show_lifecycle_banner(frm) {
	if (frm.doc.lifecycle_state !== "Inactive") return;

	const when = frm.doc.deactivated_on
		? frappe.datetime.str_to_user(frm.doc.deactivated_on)
		: null;
	const parts = [__("This document is inactive — it has been withdrawn from use.")];
	if (when) parts.push(__("Withdrawn on {0}", [when]));
	if (frm.doc.deactivated_by) parts.push(__("by {0}", [frm.doc.deactivated_by]));
	if (frm.doc.deactivation_reason) parts.push(__("Reason: {0}", [frm.doc.deactivation_reason]));

	frm.dashboard.add_comment(parts.join(" · "), "red", true);
	frm.set_intro(
		__("Nothing has been deleted. The file, its content and every version are kept — only Drive sharing was revoked."),
		"orange"
	);
}

function add_lifecycle_button(frm) {
	if (!frappe.user.has_role("System Manager")) return;

	if (frm.doc.lifecycle_state === "Inactive") {
		frm.add_custom_button(__("Reactivate"), () => confirm_reactivate(frm)).addClass("btn-primary");
		return;
	}

	frm.add_custom_button(__("Deactivate"), () => confirm_deactivate(frm), __("Lifecycle"));
}

function confirm_reactivate(frm) {
	frappe.prompt(
		[
			{
				fieldname: "reason",
				fieldtype: "Small Text",
				label: __("Why is this being brought back?"),
				description: __("Recorded on the document's timeline."),
			},
		],
		({ reason }) => {
			frappe.call({
				method: "one_fm.one_fm.doctype.document_register.document_register.reactivate",
				args: { document: frm.doc.name, reason },
				freeze: true,
				freeze_message: __("Restoring access…"),
				callback: (r) => {
					const res = (r && r.message) || {};
					if (res.share_error) {
						// The flag moved but access did not. Saying so is the
						// whole point — a silent half-success here means people
						// are told to use a document they cannot open.
						frappe.msgprint({
							title: __("Reactivated, but sharing was not restored"),
							message: __("Drive reported: {0}", [res.share_error]),
							indicator: "orange",
						});
					} else {
						frappe.show_alert({
							message: __("Reactivated and reshared."),
							indicator: "green",
						});
					}
					frm.reload_doc();
				},
			});
		},
		__("Reactivate document"),
		__("Reactivate")
	);
}

function confirm_deactivate(frm) {
	frappe.prompt(
		[
			{
				fieldname: "reason",
				fieldtype: "Small Text",
				label: __("Why is this being withdrawn?"),
				reqd: 1,
			},
		],
		({ reason }) => {
			frappe.call({
				method: "one_fm.one_fm.doctype.document_register.document_register.deactivate",
				args: { document: frm.doc.name, reason },
				freeze: true,
				freeze_message: __("Revoking access…"),
				callback: () => {
					frappe.show_alert({ message: __("Withdrawn from use."), indicator: "orange" });
					frm.reload_doc();
				},
			});
		},
		__("Deactivate document"),
		__("Deactivate")
	);
}

function add_open_button(frm) {
	if (!frm.doc.drive_file_link) return;
	frm.add_custom_button(__("Open in Drive"), () => {
		window.open(frm.doc.drive_file_link, "_blank", "noopener,noreferrer");
	});
}

function show_version_history(frm) {
	if (!frm.doc.current_version) return;

	frappe.call({
		method: "one_fm.one_fm.doctype.document_register.document_register.get_version_history",
		args: { document: frm.doc.name },
		callback: (r) => {
			const versions = (r && r.message) || [];
			if (!versions.length) return;
			frm.dashboard.add_section(render_history(versions), __("Version History"));
		},
	});
}

function render_history(versions) {
	// Newest first, and the newest is the one Drive holds — the older rows are
	// the only surviving copy of their own text, so each links to its snapshot.
	const rows = versions
		.map((v, i) => {
			const current = i === 0 ? ` <span class="indicator-pill green">${__("Current")}</span>` : "";
			const when = v.published_on ? frappe.datetime.str_to_user(v.published_on) : "—";
			const reason = frappe.utils.escape_html(v.change_reason || "");
			return `
				<tr>
					<td><a href="/app/document-revision/${encodeURIComponent(v.name)}">v${v.version}</a>${current}</td>
					<td>${frappe.utils.escape_html(v.title_at_version || "")}</td>
					<td>${when}</td>
					<td>${frappe.utils.escape_html(v.approved_by || "—")}</td>
					<td>${reason}</td>
				</tr>`;
		})
		.join("");

	return `
		<div class="table-responsive">
			<table class="table table-bordered small">
				<thead>
					<tr>
						<th>${__("Version")}</th>
						<th>${__("Title")}</th>
						<th>${__("Published")}</th>
						<th>${__("Approved by")}</th>
						<th>${__("Change reason")}</th>
					</tr>
				</thead>
				<tbody>${rows}</tbody>
			</table>
		</div>`;
}
