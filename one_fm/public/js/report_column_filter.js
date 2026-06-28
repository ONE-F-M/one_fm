// Spreadsheet-Style Column Filters for Frappe Script Reports
// Reusable component: frappe.ui.ReportColumnFilter
// Usage: new frappe.ui.ReportColumnFilter(report_instance)

frappe.provide("frappe.ui");

frappe.ui.ReportColumnFilter = class ReportColumnFilter {
	constructor(report) {
		this.report = report;
		this.datatable = report.datatable;
		this.column_filters = {};  // { fieldname: { type: "checklist"|"date", selected: Set|{from, to} } }
		this.original_data = null;
		this.active_dropdown = null;
		this.$status_bar = null;
		this.clear_all_btn = null;

		this.init();
	}

	init() {
		// Store original data on first load
		this.store_original_data();
		// Inject filter icons into column headers
		this.inject_filter_icons();
		// Setup status bar
		this.setup_status_bar();
		// Setup global clear button
		this.setup_clear_all_button();
		// Listen for clicks outside dropdown
		this.setup_outside_click_handler();
		// Listen for Escape key
		this.setup_escape_handler();
	}

	store_original_data() {
		// Deep copy the current data as the baseline
		if (!this.original_data) {
			let data = this.report.data;
			if (this.report.raw_data && this.report.raw_data.add_total_row && !this.report.report_settings.tree) {
				// Exclude the total row from original data
				data = data.slice(0, -1);
			}
			this.original_data = data.map(row => Object.assign({}, row));
		}
	}

	refresh_after_data_reload() {
		// Called when the report re-fetches data from server (e.g., top-bar filter change)
		this.original_data = null;
		this.column_filters = {};
		this.store_original_data();
		this.inject_filter_icons();
		this.update_status_bar();
		this.update_clear_all_visibility();
	}

	// ─── Header Icon Injection ───────────────────────────────────────

	inject_filter_icons() {
		const $wrapper = $(this.report.$report);
		const $header_cells = $wrapper.find(".dt-header .dt-cell");
		const columns = this.report.columns.filter(col => !col.hidden);

		$header_cells.each((idx, cell) => {
			const $cell = $(cell);
			// Skip the row number column (index 0) and serial number columns
			if (idx === 0) return;

			// Don't inject twice
			if ($cell.find(".column-filter-icon").length) return;

			const col_index = idx - 1; // offset for row number column
			if (col_index < 0 || col_index >= columns.length) return;

			const column = columns[col_index];
			const fieldname = column.fieldname;

			const $icon = $(`<span class="column-filter-icon" data-fieldname="${fieldname}"
				title="${__("Filter")}">
				${frappe.utils.icon("filter", "xs")}
			</span>`);

			$cell.find(".dt-cell__content").append($icon);

			// Mark as active if filter exists
			if (this.column_filters[fieldname]) {
				$cell.addClass("column-filter-active");
			}

			$icon.on("click", (e) => {
				e.stopPropagation();
				e.preventDefault();
				this.toggle_dropdown(fieldname, $cell, column);
			});
		});
	}

	// ─── Dropdown Toggle ─────────────────────────────────────────────

	toggle_dropdown(fieldname, $header_cell, column) {
		// If same dropdown is open, close it
		if (this.active_dropdown && this.active_dropdown.fieldname === fieldname) {
			this.close_dropdown();
			return;
		}

		// Close any existing dropdown
		this.close_dropdown();

		// Determine column type
		const is_date = column.fieldtype === "Date" || column.fieldtype === "Datetime";

		if (is_date) {
			this.open_date_dropdown(fieldname, $header_cell, column);
		} else {
			this.open_checklist_dropdown(fieldname, $header_cell, column);
		}
	}

	// ─── Checklist Dropdown ──────────────────────────────────────────

	open_checklist_dropdown(fieldname, $header_cell, column) {
		// Get unique values from currently visible rows (cross-column cascading)
		const visible_values = this.get_cascaded_values(fieldname);
		const previously_selected = this.column_filters[fieldname]
			? this.column_filters[fieldname].selected
			: null;

		// Build dropdown HTML
		const $dropdown = this.build_checklist_dropdown(fieldname, visible_values, previously_selected, column);

		// Position and show
		this.position_dropdown($dropdown, $header_cell);
		$("body").append($dropdown);

		this.active_dropdown = {
			fieldname: fieldname,
			$el: $dropdown,
			$header_cell: $header_cell,
			column: column
		};

		// Focus search input
		$dropdown.find(".cf-search-input").focus();
	}

	get_cascaded_values(target_fieldname) {
		// Return unique values for target_fieldname, considering all OTHER column filters
		let data = this.original_data;

		// Apply all filters EXCEPT the target column
		for (const [fn, filter_info] of Object.entries(this.column_filters)) {
			if (fn === target_fieldname) continue;
			data = this.apply_single_filter(data, fn, filter_info);
		}

		// Extract unique values
		const values = new Set();
		let has_blanks = false;

		data.forEach(row => {
			const val = row[target_fieldname];
			if (val === null || val === undefined || val === "") {
				has_blanks = true;
			} else {
				values.add(String(val));
			}
		});

		// Sort values
		const sorted = Array.from(values).sort((a, b) => {
			// Try numeric sort first
			const num_a = parseFloat(a);
			const num_b = parseFloat(b);
			if (!isNaN(num_a) && !isNaN(num_b)) return num_a - num_b;
			return a.localeCompare(b);
		});

		return { values: sorted, has_blanks: has_blanks };
	}

	build_checklist_dropdown(fieldname, value_data, previously_selected, column) {
		const { values, has_blanks } = value_data;

		const $dropdown = $(`<div class="column-filter-dropdown"></div>`);

		// Search box
		const $search_wrapper = $(`<div class="cf-search-wrapper">
			<input type="text" class="cf-search-input" placeholder="${__("Search")}...">
		</div>`);
		$dropdown.append($search_wrapper);

		// Actions row (Select All / Clear)
		const $actions = $(`<div class="cf-actions-row">
			<span class="cf-action-link cf-select-all">${__("Select All")}</span>
			<span class="cf-action-link cf-clear-all-items">${__("Clear")}</span>
		</div>`);
		$dropdown.append($actions);

		// Checklist
		const $checklist = $(`<div class="cf-checklist"></div>`);

		// Build items
		const all_items = [];

		// Add (Blanks) first if applicable
		if (has_blanks) {
			const is_checked = previously_selected
				? previously_selected.has("__blanks__")
				: true;
			const $blank_item = this.build_check_item("__blanks__", __("(Blanks)"), is_checked, true);
			$checklist.append($blank_item);
			all_items.push({ value: "__blanks__", $el: $blank_item, label: __("(Blanks)") });
		}

		values.forEach(val => {
			const is_checked = previously_selected
				? previously_selected.has(val)
				: true;
			const display_label = val;
			const $item = this.build_check_item(val, display_label, is_checked, false);
			$checklist.append($item);
			all_items.push({ value: val, $el: $item, label: display_label });
		});

		$dropdown.append($checklist);

		// No results message (hidden initially)
		const $no_results = $(`<div class="cf-no-results" style="display:none;">${__("No matching values found.")}</div>`);
		$dropdown.append($no_results);

		// Footer with OK button
		const $footer = $(`<div class="cf-footer">
			<button class="cf-ok-btn">${__("OK")}</button>
		</div>`);
		$dropdown.append($footer);

		// ─── Event handlers ───

		// Search
		$search_wrapper.find(".cf-search-input").on("input", function () {
			const query = $(this).val().toLowerCase();
			let visible_count = 0;

			all_items.forEach(item => {
				const matches = item.label.toLowerCase().includes(query);
				item.$el.toggle(matches);
				if (matches) visible_count++;
			});

			$no_results.toggle(visible_count === 0);
		});

		// Select All
		$actions.find(".cf-select-all").on("click", () => {
			all_items.forEach(item => {
				if (item.$el.is(":visible")) {
					item.$el.find("input[type=checkbox]").prop("checked", true);
				}
			});
		});

		// Clear
		$actions.find(".cf-clear-all-items").on("click", () => {
			all_items.forEach(item => {
				if (item.$el.is(":visible")) {
					item.$el.find("input[type=checkbox]").prop("checked", false);
				}
			});
		});

		// OK button
		$footer.find(".cf-ok-btn").on("click", () => {
			this.apply_checklist_filter(fieldname, all_items, has_blanks);
		});

		// Prevent dropdown close when clicking inside
		$dropdown.on("click", (e) => {
			e.stopPropagation();
		});

		return $dropdown;
	}

	build_check_item(value, label, is_checked, is_blanks) {
		const escaped_value = $("<div>").text(value).html();
		const escaped_label = $("<div>").text(label).html();
		const blanks_class = is_blanks ? "cf-blanks-item" : "";

		const $item = $(`<div class="cf-check-item ${blanks_class}" data-value="${escaped_value}">
			<input type="checkbox" ${is_checked ? "checked" : ""}>
			<label>${escaped_label}</label>
		</div>`);

		// Toggle checkbox when clicking the row
		$item.on("click", function (e) {
			if (e.target.tagName !== "INPUT") {
				const $cb = $(this).find("input[type=checkbox]");
				$cb.prop("checked", !$cb.prop("checked"));
			}
		});

		return $item;
	}

	apply_checklist_filter(fieldname, all_items, has_blanks) {
		// Collect checked values
		const selected = new Set();
		let all_checked = true;
		const total_items = all_items.length;

		all_items.forEach(item => {
			const is_checked = item.$el.find("input[type=checkbox]").prop("checked");
			if (is_checked) {
				selected.add(item.value);
			} else {
				all_checked = false;
			}
		});

		// If all items are checked, remove the filter for this column
		if (all_checked || selected.size === total_items) {
			delete this.column_filters[fieldname];
		} else if (selected.size === 0) {
			// Nothing selected — show nothing
			this.column_filters[fieldname] = { type: "checklist", selected: new Set(["__impossible__"]) };
		} else {
			this.column_filters[fieldname] = { type: "checklist", selected: selected };
		}

		this.close_dropdown();
		this.apply_all_filters();
	}

	// ─── Date Range Dropdown ─────────────────────────────────────────

	open_date_dropdown(fieldname, $header_cell, column) {
		const existing = this.column_filters[fieldname];
		const from_val = existing && existing.from ? existing.from : "";
		const to_val = existing && existing.to ? existing.to : "";

		const $dropdown = $(`<div class="column-filter-dropdown">
			<div class="cf-date-range-wrapper">
				<div>
					<label>${__("From Date")}</label>
					<input type="date" class="cf-date-from" value="${from_val}">
				</div>
				<div>
					<label>${__("To Date")}</label>
					<input type="date" class="cf-date-to" value="${to_val}">
				</div>
			</div>
			<div class="cf-actions-row">
				<span class="cf-action-link cf-date-clear">${__("Clear")}</span>
			</div>
			<div class="cf-footer">
				<button class="cf-ok-btn">${__("OK")}</button>
			</div>
		</div>`);

		// Clear date filter
		$dropdown.find(".cf-date-clear").on("click", () => {
			$dropdown.find(".cf-date-from").val("");
			$dropdown.find(".cf-date-to").val("");
		});

		// OK button
		$dropdown.find(".cf-ok-btn").on("click", () => {
			const from_date = $dropdown.find(".cf-date-from").val();
			const to_date = $dropdown.find(".cf-date-to").val();

			if (!from_date && !to_date) {
				// Remove filter
				delete this.column_filters[fieldname];
			} else {
				this.column_filters[fieldname] = {
					type: "date",
					from: from_date || null,
					to: to_date || null
				};
			}

			this.close_dropdown();
			this.apply_all_filters();
		});

		// Prevent close on click inside
		$dropdown.on("click", (e) => {
			e.stopPropagation();
		});

		// Position and show
		this.position_dropdown($dropdown, $header_cell);
		$("body").append($dropdown);

		this.active_dropdown = {
			fieldname: fieldname,
			$el: $dropdown,
			$header_cell: $header_cell,
			column: column
		};
	}

	// ─── Filter Application Engine ───────────────────────────────────

	apply_all_filters() {
		let filtered_data = this.original_data;

		for (const [fieldname, filter_info] of Object.entries(this.column_filters)) {
			filtered_data = this.apply_single_filter(filtered_data, fieldname, filter_info);
		}

		// Refresh the datatable with filtered data
		const columns = this.report.columns.filter(col => !col.hidden);
		this.datatable.refresh(filtered_data, columns);

		// Re-inject filter icons (datatable re-renders headers)
		setTimeout(() => {
			this.inject_filter_icons();
			this.update_header_highlights();
		}, 50);

		// Update status bar
		this.update_status_bar(filtered_data.length);

		// Update clear all button visibility
		this.update_clear_all_visibility();

		// Call after_datatable_render if the report has custom logic
		if (this.report.report_settings && this.report.report_settings.after_datatable_render) {
			// Avoid re-initializing ourselves by setting a flag
			this.report._column_filter_skip_reinit = true;
			this.report.report_settings.after_datatable_render(this.datatable);
			this.report._column_filter_skip_reinit = false;
		}
	}

	apply_single_filter(data, fieldname, filter_info) {
		if (filter_info.type === "checklist") {
			const selected = filter_info.selected;
			return data.filter(row => {
				const val = row[fieldname];
				if (val === null || val === undefined || val === "") {
					return selected.has("__blanks__");
				}
				return selected.has(String(val));
			});
		} else if (filter_info.type === "date") {
			return data.filter(row => {
				const val = row[fieldname];
				if (!val) return true; // Don't filter out blanks for date range
				const date_str = String(val);
				if (filter_info.from && date_str < filter_info.from) return false;
				if (filter_info.to && date_str > filter_info.to) return false;
				return true;
			});
		}
		return data;
	}

	// ─── Header Highlights ───────────────────────────────────────────

	update_header_highlights() {
		const $wrapper = $(this.report.$report);
		const $header_cells = $wrapper.find(".dt-header .dt-cell");
		const columns = this.report.columns.filter(col => !col.hidden);

		$header_cells.each((idx, cell) => {
			const $cell = $(cell);
			if (idx === 0) return; // skip row number

			const col_index = idx - 1;
			if (col_index < 0 || col_index >= columns.length) return;

			const fieldname = columns[col_index].fieldname;
			if (this.column_filters[fieldname]) {
				$cell.addClass("column-filter-active");
			} else {
				$cell.removeClass("column-filter-active");
			}
		});
	}

	// ─── Status Bar ──────────────────────────────────────────────────

	setup_status_bar() {
		if (this.$status_bar) return;

		this.$status_bar = $(`<div class="report-column-filter-status" style="display:none;">
			<span>${__("Showing")}</span>
			<span class="cf-status-count cf-status-filtered"></span>
			<span>${__("of")}</span>
			<span class="cf-status-count cf-status-total"></span>
			<span>${__("rows")}</span>
		</div>`);

		// Insert before the report wrapper
		this.report.$report.before(this.$status_bar);
	}

	update_status_bar(filtered_count) {
		if (!this.$status_bar) return;

		const total = this.original_data ? this.original_data.length : 0;
		const shown = filtered_count !== undefined ? filtered_count : total;
		const has_active_filters = Object.keys(this.column_filters).length > 0;

		if (has_active_filters) {
			this.$status_bar.find(".cf-status-filtered").text(shown);
			this.$status_bar.find(".cf-status-total").text(total);
			this.$status_bar.show();
		} else {
			this.$status_bar.hide();
		}
	}

	// ─── Global Clear All Button ─────────────────────────────────────

	setup_clear_all_button() {
		if (this.clear_all_btn) return;

		this.clear_all_btn = this.report.page.add_inner_button(
			__("Clear All Filters"),
			() => {
				this.clear_all_filters();
			}
		);
		this.clear_all_btn.addClass("btn-danger-light");
		this.clear_all_btn.hide();
	}

	clear_all_filters() {
		this.column_filters = {};
		this.close_dropdown();
		this.apply_all_filters();
	}

	update_clear_all_visibility() {
		if (!this.clear_all_btn) return;
		const has_filters = Object.keys(this.column_filters).length > 0;
		if (has_filters) {
			this.clear_all_btn.show();
		} else {
			this.clear_all_btn.hide();
		}
	}

	// ─── Dropdown Positioning ────────────────────────────────────────

	position_dropdown($dropdown, $header_cell) {
		const rect = $header_cell[0].getBoundingClientRect();
		let left = rect.left;
		let top = rect.bottom + 2;

		// Append temporarily to measure
		$dropdown.css({ visibility: "hidden", display: "flex" });
		$("body").append($dropdown);

		const dropdown_width = $dropdown.outerWidth();
		const dropdown_height = $dropdown.outerHeight();
		const viewport_width = $(window).width();
		const viewport_height = $(window).height();

		// Adjust if overflowing right
		if (left + dropdown_width > viewport_width - 10) {
			left = viewport_width - dropdown_width - 10;
		}
		if (left < 10) left = 10;

		// Adjust if overflowing bottom
		if (top + dropdown_height > viewport_height - 10) {
			top = rect.top - dropdown_height - 2;
		}

		$dropdown.css({
			left: left + "px",
			top: top + "px",
			visibility: "visible"
		});

		// Remove from body (will be re-appended by the caller)
		$dropdown.detach();
	}

	// ─── Dropdown Close ──────────────────────────────────────────────

	close_dropdown() {
		if (this.active_dropdown) {
			this.active_dropdown.$el.remove();
			this.active_dropdown = null;
		}
	}

	// ─── Outside Click / Escape Handlers ─────────────────────────────

	setup_outside_click_handler() {
		$(document).on("click.reportColumnFilter", (e) => {
			if (this.active_dropdown) {
				const $target = $(e.target);
				// Don't close if clicking the filter icon or inside the dropdown
				if ($target.closest(".column-filter-dropdown").length ||
					$target.closest(".column-filter-icon").length) {
					return;
				}
				this.close_dropdown();
			}
		});
	}

	setup_escape_handler() {
		$(document).on("keydown.reportColumnFilter", (e) => {
			if (e.key === "Escape" && this.active_dropdown) {
				this.close_dropdown();
			}
		});
	}

	// ─── Cleanup ─────────────────────────────────────────────────────

	destroy() {
		this.close_dropdown();
		if (this.$status_bar) {
			this.$status_bar.remove();
			this.$status_bar = null;
		}
		if (this.clear_all_btn) {
			this.clear_all_btn.remove();
			this.clear_all_btn = null;
		}
		$(document).off("click.reportColumnFilter");
		$(document).off("keydown.reportColumnFilter");
	}
};
