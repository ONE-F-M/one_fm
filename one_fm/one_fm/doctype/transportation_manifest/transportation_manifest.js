// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

// Multi-Accommodation attendance-check sheet (MA2-11).
//
// Renders the daily manifest as bold, stop-by-stop banners so a supervisor runs a
// localised "Quality of Appearance" check at each camp without mixing up workers
// across camps. Relievers carry a distinct badge. Stops unlock strictly in
// sequence: only the active stop's Attendance / QOA fields are editable; earlier
// (completed) stops stay locked read-only. All gating is enforced server-side in
// one_fm/.../transportation_manifest/manifest_sheet.py — the UI only mirrors it.

const API = "one_fm.one_fm.doctype.transportation_manifest.manifest_sheet";

const ATTENDANCE_OPTIONS = ["", "Present", "Absent"];
const QOA_OPTIONS = ["", "Pass", "Fail"];
const QOA_REASON_OPTIONS = ["", "Grooming", "Uniform"];

frappe.ui.form.on("Transportation Manifest", {
	refresh(frm) {
		if (frm.is_new()) {
			frm.get_field("manifest_sheet").$wrapper.html(
				`<div class="text-muted p-3">${__("Save the manifest to run attendance checks.")}</div>`
			);
			return;
		}
		load_sheet(frm);
	},
});

function load_sheet(frm) {
	frappe.call({
		method: `${API}.get_manifest_sheet`,
		args: { manifest: frm.doc.name },
		callback(r) {
			if (r.message) {
				render_sheet(frm, r.message);
			}
		},
	});
}

function render_sheet(frm, sheet) {
	const $wrapper = frm.get_field("manifest_sheet").$wrapper;
	$wrapper.empty();

	const $sheet = $(`<div class="tm-manifest-sheet"></div>`);

	if (!sheet.stops.length) {
		$sheet.append(`<div class="text-muted p-3">${__("No passengers on this manifest yet.")}</div>`);
		$wrapper.append($sheet);
		return;
	}

	sheet.stops.forEach((stop) => {
		$sheet.append(build_stop_block(frm, sheet, stop));
	});

	$wrapper.append($sheet);
}

function build_stop_block(frm, sheet, stop) {
	const status_class = {
		Active: "tm-stop-active",
		Completed: "tm-stop-completed",
		Locked: "tm-stop-locked",
	}[stop.status];

	const adhoc_class = stop.is_adhoc ? "tm-stop-adhoc" : "";
	const $block = $(`<div class="tm-stop ${status_class} ${adhoc_class}"></div>`);

	// --- Bold banner: Stop Index + physical camp + passenger count + status ---
	const status_badge = {
		Active: `<span class="badge badge-primary">${__("In Progress")}</span>`,
		Completed: `<span class="badge badge-success">${__("Completed")}</span>`,
		Locked: `<span class="badge badge-secondary">${__("Locked")}</span>`,
	}[stop.status];

	const adhoc_badge = stop.is_adhoc
		? `<span class="badge badge-warning ml-2">${__("Detour")}</span>`
		: "";

	const $banner = $(`
		<div class="tm-stop-banner d-flex align-items-center justify-content-between p-3">
			<div class="d-flex align-items-center">
				<span class="font-weight-bold">
					${__("Stop {0}", [stop.stop_sequence])} &mdash; ${frappe.utils.escape_html(stop.accommodation_label)}
				</span>
				<span class="text-muted small ml-3">
					${__("{0} passenger(s)", [stop.passengers.length])}
				</span>
			</div>
			<div class="d-flex align-items-center">
				${status_badge}${adhoc_badge}
			</div>
		</div>
	`);
	$block.append($banner);

	// --- Stop action buttons (server enforces the real gating) ---
	if (sheet.can_edit) {
		const $actions = build_stop_actions(frm, sheet, stop);
		if ($actions) {
			$banner.find("> div:last-child").prepend($actions);
		}
	}

	// --- Passenger rows ---
	const $rows = $(`<div class="${stop.editable ? "" : "tm-locked-rows"}"></div>`);
	stop.passengers.forEach((p) => {
		$rows.append(build_passenger_row(frm, sheet, stop, p));
	});
	$block.append($rows);

	return $block;
}

function build_stop_actions(frm, sheet, stop) {
	const $actions = $(`<span class="mr-3"></span>`);

	if (stop.can_trigger) {
		const $btn = $(
			`<button class="btn btn-sm btn-primary">${__("Trigger Attendance Check")}</button>`
		);
		$btn.on("click", () => trigger_stop(frm, stop.stop_sequence));
		$actions.append($btn);
		return $actions;
	}

	if (stop.can_complete) {
		const $save = $(`<button class="btn btn-sm btn-primary mr-2">${__("Save Checks")}</button>`);
		$save.on("click", () => save_stop(frm, sheet, stop.stop_sequence));
		const $done = $(
			`<button class="btn btn-sm btn-success">${__("Complete & Lock Stop {0}", [stop.stop_sequence])}</button>`
		);
		$done.on("click", () => complete_stop(frm, sheet, stop.stop_sequence));
		$actions.append($save).append($done);
		return $actions;
	}

	return null;
}

function build_passenger_row(frm, sheet, stop, p) {
	const $row = $(`<div class="tm-passenger-row d-flex align-items-center p-3"></div>`);

	// Name + reliever badge (relievers = rows carrying an assigned reliever_employee)
	const reliever_badge = p.is_reliever
		? `<span class="badge tm-reliever-badge ml-2">${__("Reliever")}</span>`
		: "";
	const reliever_name = p.is_reliever && p.reliever_employee_name
		? `<div class="small text-muted">${__("Reliever")}: ${frappe.utils.escape_html(p.reliever_employee_name)}</div>`
		: "";

	const $info = $(`
		<div class="flex-grow-1">
			<div class="font-weight-bold">
				${frappe.utils.escape_html(p.employee_name || p.employee || "")}${reliever_badge}
			</div>
			<div class="small text-muted">${frappe.utils.escape_html(p.employee || "")}</div>
			${reliever_name}
		</div>
	`);
	$row.append($info);

	// Attendance + QOA columns
	const $checks = $(`<div class="d-flex align-items-center"></div>`);
	if (stop.editable && sheet.can_edit) {
		$checks.append(build_editable_checks(frm, sheet, stop, p));
	} else {
		$checks.append(build_readonly_checks(p));
	}
	$row.append($checks);

	return $row;
}

function build_readonly_checks(p) {
	const badge = (label, value, cls) =>
		`<div class="mr-4 text-center">
			<div class="small text-muted">${label}</div>
			<div class="${cls}">${value ? frappe.utils.escape_html(value) : "&mdash;"}</div>
		</div>`;

	let html = badge(__("Attendance"), p.attendance_status, "font-weight-bold");
	html += badge(__("QOA"), p.qoa_status, "font-weight-bold");
	if (p.qoa_status === "Fail" && p.qoa_reason) {
		html += badge(__("Reason"), p.qoa_reason, "small");
	}
	return $(`<div class="d-flex align-items-center">${html}</div>`);
}

function build_editable_checks(frm, sheet, stop, p) {
	const $container = $(`<div class="d-flex align-items-center"></div>`);

	// Attendance Status
	const $att = build_select(__("Attendance"), ATTENDANCE_OPTIONS, p.attendance_status);
	$att.find("select").on("change", function () {
		p.attendance_status = this.value;
		// Present resets nothing here; Absent clears QOA client-side to mirror the controller.
		if (p.attendance_status === "Absent") {
			p.qoa_status = null;
			p.qoa_reason = null;
		}
		re_render_active_stop(frm, sheet, stop);
	});
	$container.append($att);

	// QOA Status — only meaningful when Present
	const qoa_disabled = p.attendance_status === "Absent" || !p.attendance_status;
	const $qoa = build_select(__("QOA"), QOA_OPTIONS, p.qoa_status, qoa_disabled);
	$qoa.find("select").on("change", function () {
		p.qoa_status = this.value;
		if (p.qoa_status !== "Fail") {
			p.qoa_reason = null;
		}
		re_render_active_stop(frm, sheet, stop);
	});
	$container.append($qoa);

	// QOA Reason — only when QOA failed
	if (p.qoa_status === "Fail") {
		const $reason = build_select(__("Reason"), QOA_REASON_OPTIONS, p.qoa_reason);
		$reason.find("select").on("change", function () {
			p.qoa_reason = this.value;
		});
		$container.append($reason);
	}

	return $container;
}

function build_select(label, options, value, disabled) {
	const opts = options
		.map((o) => `<option value="${o}" ${o === (value || "") ? "selected" : ""}>${o || "—"}</option>`)
		.join("");
	return $(`
		<div class="mr-3 text-center">
			<div class="small text-muted">${label}</div>
			<select class="form-control form-control-sm" ${disabled ? "disabled" : ""}>${opts}</select>
		</div>
	`);
}

function re_render_active_stop(frm, sheet, stop) {
	// Re-render just the active stop block in place so conditional fields
	// (QOA reason, disabled QOA on Absent) update without a server round-trip.
	const $sheet = frm.get_field("manifest_sheet").$wrapper.find(".tm-manifest-sheet");
	const $blocks = $sheet.children(".tm-stop");
	const index = sheet.stops.indexOf(stop);
	if (index < 0 || !$blocks.eq(index).length) {
		return;
	}
	$blocks.eq(index).replaceWith(build_stop_block(frm, sheet, stop));
}

function collect_stop_updates(stop) {
	return stop.passengers.map((p) => ({
		row_name: p.row_name,
		attendance_status: p.attendance_status || null,
		qoa_status: p.qoa_status || null,
		qoa_reason: p.qoa_reason || null,
	}));
}

function trigger_stop(frm, stop_sequence) {
	frappe.call({
		method: `${API}.trigger_attendance_check`,
		args: { manifest: frm.doc.name, stop_sequence },
		freeze: true,
		freeze_message: __("Unlocking stop…"),
		callback(r) {
			if (r.message) {
				frm.reload_doc();
			}
		},
	});
}

function save_stop(frm, sheet, stop_sequence, on_success) {
	const stop = sheet.stops.find((s) => s.stop_sequence === stop_sequence);
	frappe.call({
		method: `${API}.save_stop_checks`,
		args: {
			manifest: frm.doc.name,
			stop_sequence,
			updates: JSON.stringify(collect_stop_updates(stop)),
		},
		freeze: true,
		freeze_message: __("Saving checks…"),
		callback(r) {
			if (r.message) {
				if (on_success) {
					on_success();
				} else {
					frm.reload_doc();
					frappe.show_alert({ message: __("Stop {0} checks saved", [stop_sequence]), indicator: "green" });
				}
			}
		},
	});
}

function complete_stop(frm, sheet, stop_sequence) {
	// Save the active stop's edits first, then advance the pointer to lock it.
	save_stop(frm, sheet, stop_sequence, () => {
		frappe.call({
			method: `${API}.complete_stop`,
			args: { manifest: frm.doc.name, stop_sequence },
			freeze: true,
			freeze_message: __("Locking stop…"),
			callback(r) {
				if (r.message) {
					frm.reload_doc();
				}
			},
		});
	});
}
