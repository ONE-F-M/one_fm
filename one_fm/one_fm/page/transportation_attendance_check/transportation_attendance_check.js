// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

/**
 * Transportation Attendance Check — standalone Frappe page (MA2-11).
 *
 * URL: /app/transportation-attendance-check[/<Manifest_Name>]
 *
 * Groups a day's manifest passengers into bold, stop-by-stop banners so a
 * supervisor runs a localised "Quality of Appearance" check camp-by-camp without
 * mixing up workers across camps. Relievers carry a distinct badge. Stops unlock
 * strictly in sequence — only the active stop's Attendance / QOA fields are
 * editable; earlier (completed) stops stay locked read-only.
 *
 * All business rules are enforced server-side in the shared API module
 * one_fm/.../doctype/transportation_manifest/manifest_sheet.py, so this page and
 * the future Ionic screen behave identically. The page only renders + calls it.
 */

const AC_API = "one_fm.one_fm.doctype.transportation_manifest.manifest_sheet";
const AC_ATTENDANCE_OPTIONS = ["", "Present", "Absent"];
const AC_QOA_OPTIONS = ["", "Pass", "Fail"];
const AC_QOA_REASON_OPTIONS = ["", "Grooming", "Uniform"];

frappe.pages["transportation-attendance-check"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Transportation Attendance Check"),
		single_column: true,
	});

	const $container = $(wrapper).find(".layout-main-section");
	$container.empty();

	// Per-page state. `sheet` is the last structure returned by the server;
	// `manifest` is the manifest currently displayed.
	const state = { sheet: null, manifest: null };

	// --- Filter toolbar (Schedule Date + Vehicle) ---
	// Plain bordered row, not a frappe-card (the card clips dropdown overflow).
	const $toolbar = $(`
		<div class="p-3 mb-4 border rounded">
			<div class="row">
				<div class="col-md-4 mb-2" data-fld="date"></div>
				<div class="col-md-4 mb-2" data-fld="vehicle"></div>
				<div class="col-md-4 mb-2" data-fld="btn"></div>
			</div>
		</div>
	`);
	$container.append($toolbar);
	const $body = $(`<div class="tm-manifest-sheet"></div>`);
	$container.append($body);

	const ctx = { state, $body };

	ctx.date_field = frappe.ui.form.make_control({
		parent: $toolbar.find('[data-fld="date"]').get(0),
		df: {
			fieldtype: "Date",
			label: __("Schedule Date"),
			fieldname: "schedule_date",
			reqd: 1,
		},
		render_input: true,
	});
	ctx.date_field.set_value(frappe.datetime.get_today());

	// Real Link control (server-side search across all Vehicles). The parent MUST
	// be a DOM node, not a jQuery object — otherwise the Link's autocomplete never
	// initialises (that was the earlier "search doesn't work" bug).
	ctx.vehicle_field = frappe.ui.form.make_control({
		parent: $toolbar.find('[data-fld="vehicle"]').get(0),
		df: {
			fieldtype: "Link",
			label: __("Vehicle"),
			fieldname: "vehicle_no",
			options: "Vehicle",
		},
		render_input: true,
	});

	// Empty label spacer aligns the button's top with the two field inputs.
	const $btn_wrap = $(`
		<div>
			<div class="clearfix"><label class="control-label">&nbsp;</label></div>
			<button class="btn btn-primary btn-block">${__("Load Manifest")}</button>
		</div>
	`);
	$toolbar.find('[data-fld="btn"]').append($btn_wrap);
	$btn_wrap.find("button").on("click", () => load_selected(ctx));

	// Persist context so on_page_show (fires on every visit, unlike on_page_load)
	// can react to the current route without rebuilding the toolbar.
	$(wrapper).data("acCtx", ctx);
};

frappe.pages["transportation-attendance-check"].on_page_show = function (wrapper) {
	const ctx = $(wrapper).data("acCtx");
	if (!ctx) {
		return;
	}
	// Deep link: /app/transportation-attendance-check/<Manifest_Name>
	const route = frappe.get_route();
	const manifest_name = route.length > 1 ? route.slice(1).join("/") : "";

	if (manifest_name && manifest_name !== ctx.state.manifest) {
		load_by_manifest(ctx, manifest_name);
	} else if (!manifest_name && !ctx.state.manifest) {
		render_empty(ctx.$body, __("Pick a schedule date and vehicle, then load the manifest."));
	}
};

function render_empty($body, message) {
	$body.html(`<div class="text-muted text-center p-5">${frappe.utils.escape_html(message)}</div>`);
}

// Resolve the manifest for the chosen vehicle + date, then load it.
function load_selected(ctx) {
	const schedule_date = ctx.date_field.get_value();
	const vehicle_no = ctx.vehicle_field.get_value();
	if (!schedule_date || !vehicle_no) {
		frappe.msgprint(__("Please choose both a schedule date and a vehicle."));
		return;
	}
	frappe.db
		.get_value("Transportation Manifest", { vehicle_no, schedule_date }, "name")
		.then((r) => {
			const name = r.message && r.message.name;
			if (!name) {
				render_empty(
					ctx.$body,
					__("No manifest found for {0} on {1}.", [vehicle_no, schedule_date])
				);
				ctx.state.manifest = null;
				return;
			}
			load_by_manifest(ctx, name);
		});
}

function load_by_manifest(ctx, manifest) {
	frappe.call({
		method: `${AC_API}.get_manifest_sheet`,
		args: { manifest },
		freeze: true,
		freeze_message: __("Loading manifest…"),
		callback(r) {
			if (!r.message) {
				render_empty(ctx.$body, __("Manifest could not be loaded."));
				return;
			}
			ctx.state.manifest = manifest;
			ctx.state.sheet = r.message;
			// Keep the toolbar in sync when arriving via a deep link.
			if (r.message.schedule_date && ctx.date_field.get_value() !== r.message.schedule_date) {
				ctx.date_field.set_value(r.message.schedule_date);
			}
			if (r.message.vehicle_no && ctx.vehicle_field.get_value() !== r.message.vehicle_no) {
				ctx.vehicle_field.set_value(r.message.vehicle_no);
			}
			render_sheet(ctx.state, ctx.$body);
		},
	});
}

function apply_sheet(state, $body, sheet) {
	state.sheet = sheet;
	render_sheet(state, $body);
}

function render_sheet(state, $body) {
	const sheet = state.sheet;
	$body.empty();

	// Manifest summary header
	$body.append(`
		<div class="frappe-card p-3 mb-4 d-flex justify-content-between align-items-center">
			<div>
				<div class="font-weight-bold">${frappe.utils.escape_html(sheet.vehicle_no || "")}
					<span class="text-muted small ml-2">${frappe.utils.escape_html(sheet.license_plate || "")}</span>
				</div>
				<div class="small text-muted">${frappe.utils.escape_html(sheet.schedule_date || "")}</div>
			</div>
			<div class="small text-muted">${__("{0} stop(s)", [sheet.stops.length])}</div>
		</div>
	`);

	if (!sheet.stops.length) {
		$body.append(`<div class="text-muted text-center p-5">${__("No passengers on this manifest yet.")}</div>`);
		return;
	}

	sheet.stops.forEach((stop) => {
		$body.append(build_stop_block(state, $body, stop));
	});
}

function build_stop_block(state, $body, stop) {
	const sheet = state.sheet;
	const status_class = {
		Active: "tm-stop-active",
		Completed: "tm-stop-completed",
		Locked: "tm-stop-locked",
	}[stop.status];
	const adhoc_class = stop.is_adhoc ? "tm-stop-adhoc" : "";
	const $block = $(`<div class="tm-stop ${status_class} ${adhoc_class}"></div>`);

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
				<span class="text-muted small ml-3">${__("{0} passenger(s)", [stop.passengers.length])}</span>
			</div>
			<div class="d-flex align-items-center"></div>
		</div>
	`);
	const $banner_right = $banner.find("> div:last-child");
	if (sheet.can_edit) {
		const $actions = build_stop_actions(state, $body, stop);
		if ($actions) {
			$banner_right.append($actions);
		}
	}
	$banner_right.append(status_badge).append(adhoc_badge);
	$block.append($banner);

	const $rows = $(`<div class="${stop.editable ? "" : "tm-locked-rows"}"></div>`);
	stop.passengers.forEach((p) => {
		$rows.append(build_passenger_row(state, $body, stop, p));
	});
	$block.append($rows);

	return $block;
}

function build_stop_actions(state, $body, stop) {
	const $actions = $(`<span class="mr-3"></span>`);

	if (stop.can_trigger) {
		const $btn = $(`<button class="btn btn-sm btn-primary">${__("Trigger Attendance Check")}</button>`);
		$btn.on("click", () => trigger_stop(state, $body, stop.stop_sequence));
		$actions.append($btn);
		return $actions;
	}

	if (stop.can_complete) {
		const $save = $(`<button class="btn btn-sm btn-primary mr-2">${__("Save Checks")}</button>`);
		$save.on("click", () => save_stop(state, $body, stop.stop_sequence));
		const $done = $(
			`<button class="btn btn-sm btn-success">${__("Complete & Lock Stop {0}", [stop.stop_sequence])}</button>`
		);
		$done.on("click", () => complete_stop(state, $body, stop.stop_sequence));
		$actions.append($save).append($done);
		return $actions;
	}

	return null;
}

function build_passenger_row(state, $body, stop, p) {
	const sheet = state.sheet;
	const $row = $(`<div class="tm-passenger-row d-flex align-items-center p-3"></div>`);

	// Relievers = rows carrying an assigned reliever_employee.
	const reliever_badge = p.is_reliever
		? `<span class="badge tm-reliever-badge ml-2">${__("Reliever")}</span>`
		: "";
	const reliever_name = p.is_reliever && p.reliever_employee_name
		? `<div class="small text-muted">${__("Reliever")}: ${frappe.utils.escape_html(p.reliever_employee_name)}</div>`
		: "";

	$row.append(`
		<div class="flex-grow-1">
			<div class="font-weight-bold">
				${frappe.utils.escape_html(p.employee_name || p.employee || "")}${reliever_badge}
			</div>
			<div class="small text-muted">${frappe.utils.escape_html(p.employee || "")}</div>
			${reliever_name}
		</div>
	`);

	const $checks = $(`<div class="d-flex align-items-center"></div>`);
	if (stop.editable && sheet.can_edit) {
		$checks.append(build_editable_checks(state, $body, stop, p));
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

function build_editable_checks(state, $body, stop, p) {
	const $container = $(`<div class="d-flex align-items-center"></div>`);

	const $att = build_select(__("Attendance"), AC_ATTENDANCE_OPTIONS, p.attendance_status);
	$att.find("select").on("change", function () {
		p.attendance_status = this.value;
		if (p.attendance_status === "Absent") {
			// Mirror the controller: Absent clears QOA.
			p.qoa_status = null;
			p.qoa_reason = null;
		}
		re_render_active_stop(state, $body, stop);
	});
	$container.append($att);

	const qoa_disabled = p.attendance_status === "Absent" || !p.attendance_status;
	const $qoa = build_select(__("QOA"), AC_QOA_OPTIONS, p.qoa_status, qoa_disabled);
	$qoa.find("select").on("change", function () {
		p.qoa_status = this.value;
		if (p.qoa_status !== "Fail") {
			p.qoa_reason = null;
		}
		re_render_active_stop(state, $body, stop);
	});
	$container.append($qoa);

	if (p.qoa_status === "Fail") {
		const $reason = build_select(__("Reason"), AC_QOA_REASON_OPTIONS, p.qoa_reason);
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

function re_render_active_stop(state, $body, stop) {
	const $blocks = $body.children(".tm-stop");
	const index = state.sheet.stops.indexOf(stop);
	if (index < 0 || !$blocks.eq(index).length) {
		return;
	}
	$blocks.eq(index).replaceWith(build_stop_block(state, $body, stop));
}

function collect_stop_updates(stop) {
	return stop.passengers.map((p) => ({
		row_name: p.row_name,
		attendance_status: p.attendance_status || null,
		qoa_status: p.qoa_status || null,
		qoa_reason: p.qoa_reason || null,
	}));
}

function trigger_stop(state, $body, stop_sequence) {
	frappe.call({
		method: `${AC_API}.trigger_attendance_check`,
		args: { manifest: state.manifest, stop_sequence },
		freeze: true,
		freeze_message: __("Unlocking stop…"),
		callback(r) {
			if (r.message) {
				apply_sheet(state, $body, r.message);
			}
		},
	});
}

function save_stop(state, $body, stop_sequence, on_success) {
	const stop = state.sheet.stops.find((s) => s.stop_sequence === stop_sequence);
	frappe.call({
		method: `${AC_API}.save_stop_checks`,
		args: {
			manifest: state.manifest,
			stop_sequence,
			updates: JSON.stringify(collect_stop_updates(stop)),
		},
		freeze: true,
		freeze_message: __("Saving checks…"),
		callback(r) {
			if (!r.message) {
				return;
			}
			if (on_success) {
				on_success(r.message);
			} else {
				apply_sheet(state, $body, r.message);
				frappe.show_alert({ message: __("Stop {0} checks saved", [stop_sequence]), indicator: "green" });
			}
		},
	});
}

function complete_stop(state, $body, stop_sequence) {
	// Save the active stop's edits first, then advance the pointer to lock it.
	save_stop(state, $body, stop_sequence, () => {
		frappe.call({
			method: `${AC_API}.complete_stop`,
			args: { manifest: state.manifest, stop_sequence },
			freeze: true,
			freeze_message: __("Locking stop…"),
			callback(r) {
				if (r.message) {
					apply_sheet(state, $body, r.message);
				}
			},
		});
	});
}
