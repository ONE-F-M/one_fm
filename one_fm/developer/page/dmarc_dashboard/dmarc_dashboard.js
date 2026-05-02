frappe.pages['dmarc_dashboard'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'DMARC Monitoring Dashboard',
		single_column: true
	});

	page.set_primary_action('Refresh', () => {
		fetch_and_render(page, wrapper);
	}, 'refresh');

	fetch_and_render(page, wrapper);
}

function fetch_and_render(page, wrapper) {
	const $body = $(wrapper).find('.layout-main-section, .page-content, .frappe-page-content').first();
	if (!$body.length) return;

	if ($body.find('.dmarc-filter-bar').length === 0) {
		render_standard_filter_bar($body, page, wrapper);
	}

	const from_date = wrapper.from_date_field ? wrapper.from_date_field.get_value() : null;
	const to_date = wrapper.to_date_field ? wrapper.to_date_field.get_value() : null;

	let $stats_area = $body.find('.dmarc-stats-area');
	if (!$stats_area.length) {
		$stats_area = $('<div class="dmarc-stats-area"></div>').appendTo($body);
	}
	$stats_area.html('<div class="text-muted p-5 text-center">Updating DMARC statistics...</div>');

	frappe.call({
		method: 'one_fm.developer.page.dmarc_dashboard.dmarc_dashboard.get_dashboard_data',
		args: { from_date: from_date, to_date: to_date },
		callback: function(r) {
			$stats_area.empty();
			if (r.message && !r.message.error) {
				render_content($stats_area, r.message);
			} else {
				const err_msg = r.message ? r.message.error : 'No response from server';
				// Point 3: Use .text() to prevent XSS
				$('<div class="alert alert-danger"></div>').text('Error: ' + err_msg).appendTo($stats_area);
			}
		}
	});
}

function render_standard_filter_bar($container, page, wrapper) {
	const $filter_bar = $(`
		<div class="dmarc-filter-bar mb-4 p-3 d-flex align-items-center justify-content-between"
			 style="background: #fff; border-bottom: 1px solid #d1d8dd; margin: -15px -15px 30px -15px;">
			<div class="d-flex align-items-center">
				<div class="filter-field-wrapper mr-2" style="width: 180px;"></div>
				<div class="mx-2 text-muted small">to</div>
				<div class="filter-field-wrapper mr-2" style="width: 180px;"></div>
			</div>
			<div class="small text-muted">
				<span class="indicator-pill orange">30 Day Window</span>
			</div>
		</div>
	`).prependTo($container);

	const $wrappers = $filter_bar.find('.filter-field-wrapper');

	wrapper.from_date_field = frappe.ui.form.make_control({
		parent: $wrappers.get(0),
		df: {
			label: 'From Date', fieldtype: 'Date', fieldname: 'from_date',
			placeholder: 'From Date', only_input: true,
			change() { fetch_and_render(page, wrapper); }
		},
		render_input: true
	});

	wrapper.to_date_field = frappe.ui.form.make_control({
		parent: $wrappers.get(1),
		df: {
			label: 'To Date', fieldtype: 'Date', fieldname: 'to_date',
			placeholder: 'To Date', only_input: true,
			change() { fetch_and_render(page, wrapper); }
		},
		render_input: true
	});

	wrapper.from_date_field.set_value(frappe.datetime.add_days(frappe.datetime.nowdate(), -30));
	wrapper.to_date_field.set_value(frappe.datetime.nowdate());
}

function format_num(v) { return (v || 0).toLocaleString(); }

// Point 11: Escape HTML to prevent XSS from untrusted DMARC data
function esc(str) {
	if (!str) return '-';
	const div = document.createElement('div');
	div.appendChild(document.createTextNode(str));
	return div.innerHTML;
}

function render_content($container, data) {
	if (data.total_reports === 0) {
		$container.html('<div class="text-muted p-5 text-center">No reports found for the selected period.</div>');
		return;
	}

	const pass_rate_color = data.pass_rate >= 95 ? 'text-success' : 'text-danger';

	$container.append(`
		<div class="row mb-4">
			<div class="col-sm-3"><div class="frappe-card p-3 text-center">
				<div class="text-muted small">Total Reports</div>
				<div class="h3 font-weight-bold text-primary">${format_num(data.total_reports)}</div>
			</div></div>
			<div class="col-sm-3"><div class="frappe-card p-3 text-center">
				<div class="text-muted small">Messages Scanned</div>
				<div class="h3 font-weight-bold text-primary">${format_num(data.total_messages)}</div>
			</div></div>
			<div class="col-sm-3"><div class="frappe-card p-3 text-center">
				<div class="text-muted small">Overall Pass Rate</div>
				<div class="h3 font-weight-bold ${pass_rate_color}">${(data.pass_rate || 0).toFixed(1)}%</div>
			</div></div>
			<div class="col-sm-3"><div class="frappe-card p-3 text-center">
				<div class="text-muted small">Spoofing Attempts</div>
				<div class="h3 font-weight-bold text-danger">${format_num(data.spoofing_attempts)}</div>
			</div></div>
		</div>
		<div class="row mb-4">
			<div class="col-md-8"><div class="frappe-card p-3">
				<div class="font-weight-bold mb-3">Daily Email Volume</div>
				<div class="chart-daily-area" style="min-height: 250px;"></div>
			</div></div>
			<div class="col-md-4"><div class="frappe-card p-3">
				<div class="font-weight-bold mb-3">Overall Breakdown</div>
				<div class="chart-breakdown-area" style="min-height: 250px;"></div>
			</div></div>
		</div>
		<div class="row mb-4">
			<div class="col-md-6"><div class="frappe-card p-3">
				<div class="font-weight-bold mb-3">Top 10 Source IPs</div>
				<div class="chart-ips-area" style="min-height: 250px;"></div>
			</div></div>
			<div class="col-md-6"><div class="frappe-card p-3">
				<div class="font-weight-bold mb-3">Reports by Organization</div>
				<div class="chart-orgs-area" style="min-height: 250px;"></div>
			</div></div>
		</div>
		<div class="frappe-card p-3">
			<div class="font-weight-bold mb-3 text-danger">Recent Spoofing Alerts</div>
			<div class="table-responsive">
				<table class="table table-sm table-hover table-borderless">
					<thead><tr class="text-muted small uppercase">
						<th>Date</th><th>Source IP</th><th>Country</th>
						<th>Reverse DNS</th><th class="text-right">Msgs</th><th>Action</th>
					</tr></thead>
					<tbody class="alert-rows"></tbody>
				</table>
			</div>
		</div>
	`);

	setTimeout(() => {
		try {
			const daily_el = $container.find('.chart-daily-area').get(0);
			const breakdown_el = $container.find('.chart-breakdown-area').get(0);
			const ips_el = $container.find('.chart-ips-area').get(0);
			const orgs_el = $container.find('.chart-orgs-area').get(0);

			if (daily_el && data.daily_volume && data.daily_volume.labels && data.daily_volume.labels.length) {
				new frappe.Chart(daily_el, { data: data.daily_volume, type: 'line', height: 250, colors: ['#28a745', '#dc3545'] });
			}
			if (breakdown_el) {
				new frappe.Chart(breakdown_el, { data: data.breakdown, type: 'donut', height: 250, colors: ['#28a745', '#dc3545'] });
			}
			if (ips_el) {
				new frappe.Chart(ips_el, { data: data.top_ips, type: 'bar', height: 250, colors: ['#007bff'] });
			}
			if (orgs_el) {
				new frappe.Chart(orgs_el, { data: data.org_reports, type: 'bar', height: 250, colors: ['#17a2b8'] });
			}
		} catch (err) {
			console.error("DMARC Dashboard: Chart Render Error", err);
		}
	}, 300);

	// Point 11: Use esc() for all untrusted fields
	const $rows = $container.find('.alert-rows');
	if (data.alerts && data.alerts.length) {
		data.alerts.forEach(a => {
			const badge = a.disposition === 'reject' ? 'badge-danger' :
						  a.disposition === 'quarantine' ? 'badge-warning' : 'badge-light';
			const row_class = a.disposition === 'reject' ? 'table-danger' : '';

			$rows.append(`
				<tr class="${row_class}">
					<td class="small">${frappe.datetime.str_to_user(a.date)}</td>
					<td class="font-weight-bold">${esc(a.source_ip)}</td>
					<td>${esc(a.source_country)}</td>
					<td class="small text-muted">${esc(a.source_reverse_dns)}</td>
					<td class="text-right">${format_num(a.message_count)}</td>
					<td><span class="badge ${badge}">${esc(a.disposition)}</span></td>
				</tr>
			`);
		});
	} else {
		$rows.append('<tr><td colspan="6" class="text-center text-muted p-4">No alerts found.</td></tr>');
	}
}
