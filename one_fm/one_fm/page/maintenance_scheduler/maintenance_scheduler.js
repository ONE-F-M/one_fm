// Copyright (c) 2026, One FM and contributors
// For license information, please see license.txt

// Maintenance Scheduler
// A responsive, high-density interactive schedule grid for Maintenance Work
// Orders. It offers six time viewports (Hourly, Daily, Weekly, Monthly,
// Quarterly, Yearly), cascading location filters (Project -> Operations Site
// -> Building -> Maintenance Floor -> Space) and a day/bucket card that shows
// the first N Work Orders with the rest collapsed behind a "+X more" link.
//
// Built with Vue 3 (vendored global build at /assets/one_fm/js/vue.global.js)
// mounted into a standard Frappe Desk page, matching the transportation
// schedule pattern used elsewhere in one_fm.

const API_DATA = "one_fm.one_fm.page.maintenance_scheduler.maintenance_scheduler.get_schedule_data";
const API_OPTIONS = "one_fm.one_fm.page.maintenance_scheduler.maintenance_scheduler.get_location_options";
const VUE_ASSET = "/assets/one_fm/js/vue.global.js";

// The cascading filter levels, top -> bottom. Each depends on the one above.
const FILTER_LEVELS = [
	{ key: "project", label: __("Project") },
	{ key: "operations_site", label: __("Operations Site") },
	{ key: "building", label: __("Building") },
	{ key: "maintenance_floor", label: __("Maintenance Floor") },
	{ key: "space", label: __("Space") },
];

const VIEWS = [
	{ key: "hourly", label: __("Hourly") },
	{ key: "daily", label: __("Daily") },
	{ key: "weekly", label: __("Weekly") },
	{ key: "monthly", label: __("Monthly") },
	{ key: "quarterly", label: __("Quarterly") },
	{ key: "yearly", label: __("Yearly") },
];

const WEEKDAY_HEADERS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

frappe.pages["maintenance-scheduler"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Maintenance Scheduler"),
		single_column: true,
	});

	$(page.body).html(
		`<div class="ms-loading text-muted p-5 text-center">${__("Loading scheduler…")}</div>`
	);

	frappe.require(VUE_ASSET, () => {
		if (!window.Vue || !window.Vue.createApp) {
			$(page.body).html(
				`<div class="ms-empty p-5 text-center text-muted">${__(
					"Could not load the scheduler engine (Vue)."
				)}</div>`
			);
			return;
		}
		wrapper.ms_app = mount_app(page);
	});
};

frappe.pages["maintenance-scheduler"].on_page_show = function (wrapper) {
	if (wrapper.ms_app && wrapper.ms_app.reload) {
		wrapper.ms_app.reload();
	}
};

function mount_app(page) {
	$(page.body).html('<div id="ms-app"></div>');
	const { createApp } = window.Vue;

	const app = createApp({
		template: TEMPLATE,
		data() {
			return {
				views: VIEWS,
				filterLevels: FILTER_LEVELS,
				weekdayHeaders: WEEKDAY_HEADERS,
				view: "monthly",
				anchor: frappe.datetime.get_today(),
				periodLabel: "",
				buckets: [],
				maxVisible: 5,
				loading: false,
				// selected filter values, keyed by level
				filters: { project: "", operations_site: "", building: "", maintenance_floor: "", space: "" },
				// dropdown options, keyed by level
				options: { project: [], operations_site: [], building: [], maintenance_floor: [], space: [] },
				// bucket keys whose "+X more" has been expanded
				expanded: {},
			};
		},
		computed: {
			gridClass() {
				return `ms-grid ms-view-${this.view}`;
			},
			// Leading blank cells so the monthly calendar's first day lands under
			// the correct weekday column (Sunday = 0).
			monthLeadBlanks() {
				if (this.view !== "monthly" || !this.buckets.length) return [];
				const first = this.buckets[0];
				const lead = typeof first.weekday === "number" ? first.weekday : 0;
				return Array.from({ length: lead });
			},
			totalWorkOrders() {
				return this.buckets.reduce((n, b) => n + (b.work_orders ? b.work_orders.length : 0), 0);
			},
		},
		methods: {
			// --- data loading -------------------------------------------------
			reload() {
				this.loadData();
			},
			loadData() {
				this.loading = true;
				frappe.call({
					method: API_DATA,
					args: {
						view: this.view,
						anchor: this.anchor,
						filters: JSON.stringify(this.activeFilters()),
					},
					callback: (r) => {
						this.loading = false;
						const m = r && r.message;
						if (!m) return;
						this.buckets = m.buckets || [];
						this.periodLabel = m.period_label || "";
						this.maxVisible = m.max_visible || 5;
						this.expanded = {}; // collapse everything on each (re)load
					},
					error: () => {
						this.loading = false;
					},
				});
			},
			activeFilters() {
				const out = {};
				this.filterLevels.forEach((l) => {
					if (this.filters[l.key]) out[l.key] = this.filters[l.key];
				});
				return out;
			},
			loadOptions(level, parent) {
				frappe.call({
					method: API_OPTIONS,
					args: { level, parent: parent || undefined },
					callback: (r) => {
						this.options[level] = (r && r.message) || [];
					},
				});
			},

			// --- viewport + navigation ---------------------------------------
			setView(v) {
				if (this.view === v) return;
				this.view = v;
				this.loadData();
			},
			navigate(dir) {
				// dir: -1 (previous), 0 (today), +1 (next). The step size depends
				// on the viewport so each click moves by one visible period.
				if (dir === 0) {
					this.anchor = frappe.datetime.get_today();
				} else {
					this.anchor = this.shiftAnchor(this.anchor, dir);
				}
				this.loadData();
			},
			shiftAnchor(anchor, dir) {
				const d = frappe.datetime.str_to_obj(anchor);
				switch (this.view) {
					case "hourly":
						d.setDate(d.getDate() + dir); // +/- 1 day
						break;
					case "daily":
						d.setDate(d.getDate() + dir * 7); // +/- 1 week
						break;
					case "weekly":
					case "monthly":
						d.setMonth(d.getMonth() + dir); // +/- 1 month
						break;
					case "quarterly":
						d.setMonth(d.getMonth() + dir * 3); // +/- 1 quarter
						break;
					case "yearly":
						d.setFullYear(d.getFullYear() + dir); // +/- 1 year
						break;
				}
				return frappe.datetime.obj_to_str(d).split(" ")[0];
			},

			// --- cascading filters -------------------------------------------
			onFilterChange(level) {
				// Clear and reload every level below the one that changed.
				const idx = this.filterLevels.findIndex((l) => l.key === level);
				for (let i = idx + 1; i < this.filterLevels.length; i++) {
					const child = this.filterLevels[i].key;
					this.filters[child] = "";
					this.options[child] = [];
				}
				const next = this.filterLevels[idx + 1];
				if (next && this.filters[level]) {
					this.loadOptions(next.key, this.filters[level]);
				}
				this.loadData();
			},
			clearFilters() {
				this.filterLevels.forEach((l, i) => {
					this.filters[l.key] = "";
					if (i > 0) this.options[l.key] = [];
				});
				this.loadData();
			},
			filterDisabled(level) {
				const idx = this.filterLevels.findIndex((l) => l.key === level);
				if (idx === 0) return false; // Project is always enabled
				return !this.filters[this.filterLevels[idx - 1].key];
			},

			// --- work-order card helpers -------------------------------------
			visibleOrders(bucket) {
				if (this.expanded[bucket.key]) return bucket.work_orders;
				return bucket.work_orders.slice(0, this.maxVisible);
			},
			hiddenCount(bucket) {
				const n = bucket.work_orders.length - this.maxVisible;
				return this.expanded[bucket.key] ? 0 : Math.max(n, 0);
			},
			toggleExpand(bucket) {
				this.expanded = { ...this.expanded, [bucket.key]: !this.expanded[bucket.key] };
			},
			openWorkOrder(wo) {
				window.open(`/app/maintenance-work-order/${encodeURIComponent(wo.name)}`, "_blank");
			},
			statusClass(status) {
				return {
					Open: "ms-status-open",
					Dispatched: "ms-status-dispatched",
					"On Hold - Parts Required": "ms-status-hold",
					Completed: "ms-status-completed",
				}[status] || "ms-status-open";
			},
			typeClass(type) {
				return type === "Reactive Maintenance" ? "ms-type-reactive" : "ms-type-preventive";
			},
			escape(v) {
				return frappe.utils.escape_html(v == null ? "" : String(v));
			},
			showTime(wo) {
				// The hourly view already groups by hour; other views benefit from
				// the exact time badge on each card.
				return this.view !== "hourly";
			},
		},
		mounted() {
			this.loadOptions("project");
			this.loadData();
		},
	});

	const vm = app.mount("#ms-app");
	return vm;
}

// The template is kept as a single string so the page needs no build step.
const TEMPLATE = `
<div class="ms-wrapper">
	<div class="ms-toolbar">
		<div class="ms-views btn-group">
			<button v-for="v in views" :key="v.key"
				class="btn btn-sm"
				:class="view === v.key ? 'btn-primary' : 'btn-default'"
				@click="setView(v.key)">{{ v.label }}</button>
		</div>

		<div class="ms-nav">
			<button class="btn btn-default btn-sm" @click="navigate(-1)" :title="__('Previous')">
				<i class="fa fa-chevron-left"></i>
			</button>
			<button class="btn btn-default btn-sm" @click="navigate(0)">{{ __("Today") }}</button>
			<button class="btn btn-default btn-sm" @click="navigate(1)" :title="__('Next')">
				<i class="fa fa-chevron-right"></i>
			</button>
			<span class="ms-period">{{ periodLabel }}</span>
		</div>

		<div class="ms-count text-muted small">
			{{ totalWorkOrders }} {{ __("Work Order(s)") }}
		</div>
	</div>

	<div class="ms-filters">
		<div class="ms-filter-group" v-for="level in filterLevels" :key="level.key">
			<span class="ms-filter-label">{{ level.label }}</span>
			<select class="form-control input-sm"
				:disabled="filterDisabled(level.key)"
				v-model="filters[level.key]"
				@change="onFilterChange(level.key)">
				<option value="">{{ __("All") }}</option>
				<option v-for="opt in options[level.key]" :key="opt.value" :value="opt.value">
					{{ opt.label }}
				</option>
			</select>
		</div>
		<button class="btn btn-default btn-sm ms-clear" @click="clearFilters">
			<i class="fa fa-times"></i> {{ __("Clear") }}
		</button>
	</div>

	<div class="ms-board-scroll">
		<div v-if="loading" class="ms-empty text-muted">{{ __("Loading…") }}</div>

		<div v-else-if="!buckets.length" class="ms-empty text-muted">
			<div class="ms-empty-icon">🗓️</div>
			<p>{{ __("No Work Orders for this period.") }}</p>
		</div>

		<!-- Monthly calendar: weekday header + aligned day cells -->
		<template v-else-if="view === 'monthly'">
			<div class="ms-weekday-row">
				<div class="ms-weekday" v-for="wd in weekdayHeaders" :key="wd">{{ __(wd) }}</div>
			</div>
			<div :class="gridClass">
				<div class="ms-cal-blank" v-for="(b, i) in monthLeadBlanks" :key="'blank-' + i"></div>
				<div v-for="bucket in buckets" :key="bucket.key"
					class="ms-cell ms-day-cell" :class="{ 'ms-today': bucket.is_today }">
					<div class="ms-cell-head">
						<span class="ms-cell-daynum">{{ bucket.label }}</span>
						<span class="ms-cell-sub">{{ bucket.sublabel }}</span>
					</div>
					<div class="ms-orders">
						<div v-for="wo in visibleOrders(bucket)" :key="wo.name"
							class="ms-order" :class="typeClass(wo.maintenance_type)"
							:title="wo.object_name + ' · ' + wo.status"
							@click="openWorkOrder(wo)">
							<span class="ms-order-dot" :class="statusClass(wo.status)"></span>
							<span v-if="showTime(wo)" class="ms-order-time">{{ wo.time_label }}</span>
							<span class="ms-order-title">{{ wo.object_name || wo.name }}</span>
						</div>
						<button v-if="hiddenCount(bucket)" class="ms-more" @click.stop="toggleExpand(bucket)">
							+{{ hiddenCount(bucket) }} {{ __("more") }}
						</button>
						<button v-else-if="expanded[bucket.key] && bucket.work_orders.length > maxVisible"
							class="ms-more" @click.stop="toggleExpand(bucket)">
							{{ __("Show less") }}
						</button>
					</div>
				</div>
			</div>
		</template>

		<!-- Hourly: vertical stack of 24 hour rows -->
		<div v-else-if="view === 'hourly'" class="ms-grid ms-view-hourly">
			<div v-for="bucket in buckets" :key="bucket.key"
				class="ms-hour-row" :class="{ 'ms-current': bucket.is_current }">
				<div class="ms-hour-label">
					<div class="ms-hour-24">{{ bucket.label }}</div>
					<div class="ms-hour-12 text-muted small">{{ bucket.sublabel }}</div>
				</div>
				<div class="ms-hour-orders">
					<div v-for="wo in visibleOrders(bucket)" :key="wo.name"
						class="ms-order ms-order-inline" :class="typeClass(wo.maintenance_type)"
						:title="wo.object_name + ' · ' + wo.status"
						@click="openWorkOrder(wo)">
						<span class="ms-order-dot" :class="statusClass(wo.status)"></span>
						<span class="ms-order-time">{{ wo.time_label }}</span>
						<span class="ms-order-title">{{ wo.object_name || wo.name }}</span>
						<span class="ms-order-status">{{ wo.status }}</span>
					</div>
					<span v-if="!bucket.work_orders.length" class="ms-hour-empty text-muted small">—</span>
					<button v-if="hiddenCount(bucket)" class="ms-more" @click.stop="toggleExpand(bucket)">
						+{{ hiddenCount(bucket) }} {{ __("more") }}
					</button>
					<button v-else-if="expanded[bucket.key] && bucket.work_orders.length > maxVisible"
						class="ms-more" @click.stop="toggleExpand(bucket)">
						{{ __("Show less") }}
					</button>
				</div>
			</div>
		</div>

		<!-- Daily / Weekly / Quarterly / Yearly: uniform bucket cards -->
		<div v-else :class="gridClass">
			<div v-for="bucket in buckets" :key="bucket.key"
				class="ms-cell ms-bucket-cell"
				:class="{ 'ms-today': bucket.is_today, 'ms-current': bucket.is_current }">
				<div class="ms-cell-head">
					<span class="ms-cell-title">{{ bucket.label }}</span>
					<span class="ms-cell-sub">{{ bucket.sublabel }}</span>
					<span class="ms-cell-badge" v-if="bucket.work_orders.length">{{ bucket.work_orders.length }}</span>
				</div>
				<div class="ms-orders">
					<div v-for="wo in visibleOrders(bucket)" :key="wo.name"
						class="ms-order" :class="typeClass(wo.maintenance_type)"
						:title="wo.object_name + ' · ' + wo.status"
						@click="openWorkOrder(wo)">
						<span class="ms-order-dot" :class="statusClass(wo.status)"></span>
						<span v-if="showTime(wo)" class="ms-order-time">{{ wo.time_label }}</span>
						<span class="ms-order-title">{{ wo.object_name || wo.name }}</span>
					</div>
					<button v-if="hiddenCount(bucket)" class="ms-more" @click.stop="toggleExpand(bucket)">
						+{{ hiddenCount(bucket) }} {{ __("more") }}
					</button>
					<button v-else-if="expanded[bucket.key] && bucket.work_orders.length > maxVisible"
						class="ms-more" @click.stop="toggleExpand(bucket)">
						{{ __("Show less") }}
					</button>
				</div>
			</div>
		</div>
	</div>
</div>
`;
