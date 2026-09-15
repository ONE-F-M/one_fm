// WI-003352: colour-code Leave Application calendar entries by leave type.
//
// hrms registers frappe.views.calendar["Leave Application"] with its own
// field_map / get_events_method (hrms.hr.doctype.leave_application.leave_application.get_events).
// We are not allowed to edit hrms directly, so this file runs after hrms's
// own doctype_calendar_js (loaded via the same hook, one_fm's script loads
// after the app's own bundle) and patches the already-registered config:
//   - points get_events_method at our wrapper, which adds `leave_type` and
//     `color` to every event, deterministically keyed off Leave Type
//   - adds a `color` entry to field_map so frappe's calendar view picks up
//     the per-event colour instead of a single style for every entry
//   - draws a small legend under the calendar mapping colour to leave type,
//     reusing the same colour list the server assigns from so it always
//     agrees with what is actually drawn.
//
// This mirrors how one_fm already patches other upstream doctype_calendar_js
// configuration in the doctype_js hook style (see leave_type.js / leave_application.js
// in this folder for the same "customise the standard controller" pattern).

frappe.views.calendars = frappe.views.calendars || {};

$(document).on("app_ready", function () {
	patch_leave_application_calendar();
});

function patch_leave_application_calendar() {
	const config = frappe.views.calendar && frappe.views.calendar["Leave Application"];
	if (!config) {
		// hrms hasn't registered its config yet (or calendar view not loaded) - retry shortly.
		setTimeout(patch_leave_application_calendar, 500);
		return;
	}
	if (config.__one_fm_leave_type_colour_patch_applied) {
		return;
	}
	config.__one_fm_leave_type_colour_patch_applied = true;

	config.get_events_method = "one_fm.overrides.leave_application.get_leave_application_calendar_events";
	config.field_map = Object.assign({}, config.field_map, { color: "color" });

	const original_get_css_class = config.get_css_class;
	config.get_css_class = function (data) {
		// Individual event colour is applied via field_map.color by the
		// calendar renderer; keep any status-based class hrms already sets.
		return original_get_css_class ? original_get_css_class(data) : undefined;
	};

	const original_on_render = config.options && config.options.onRender;
	config.options = config.options || {};

	render_leave_type_legend();
}

// Same palette and ordering rule as one_fm.overrides.leave_application._get_leave_type_colour
// so the legend always matches the colours actually drawn on events.
const ONE_FM_LEAVE_TYPE_CALENDAR_COLOURS = [
	"#2490EF", // blue
	"#29CD42", // green
	"#CB2929", // red
	"#F4B912", // yellow
	"#743EE4", // purple
	"#E8399D", // pink
	"#00B0AF", // teal
	"#FF7846", // orange
];

function render_leave_type_legend() {
	frappe.db.get_list("Leave Type", { fields: ["name"], limit: 0, order_by: "name" }).then((leave_types) => {
		const $existing = $(".one-fm-leave-type-calendar-legend");
		if ($existing.length) {
			$existing.remove();
		}
		if (!leave_types || !leave_types.length) {
			return;
		}
		const $legend = $(`<div class="one-fm-leave-type-calendar-legend" style="display:flex;flex-wrap:wrap;gap:12px;padding:8px 15px;font-size:12px;"></div>`);
		leave_types.forEach((row, index) => {
			const colour = ONE_FM_LEAVE_TYPE_CALENDAR_COLOURS[index % ONE_FM_LEAVE_TYPE_CALENDAR_COLOURS.length];
			$legend.append(
				`<span class="one-fm-leave-type-legend-item" title="${frappe.utils.escape_html(row.name)}" style="display:inline-flex;align-items:center;gap:5px;">
					<span style="width:10px;height:10px;border-radius:2px;background:${colour};display:inline-block;"></span>
					${frappe.utils.escape_html(row.name)}
				</span>`
			);
		});

		const attach_legend = () => {
			const $calendar_wrapper = $(".calendar-container, .frappe-calendar").first();
			if ($calendar_wrapper.length) {
				$calendar_wrapper.before($legend);
				return true;
			}
			return false;
		};

		if (!attach_legend()) {
			// Calendar DOM may not be ready yet on first navigation to the view.
			setTimeout(attach_legend, 800);
		}
	});
}

frappe.router.on("change", () => {
	if (frappe.get_route().join("/").toLowerCase().includes("leave application/view/calendar")) {
		setTimeout(patch_leave_application_calendar, 300);
	}
});
