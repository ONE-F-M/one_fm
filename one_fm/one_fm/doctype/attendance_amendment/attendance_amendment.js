// Copyright (c) 2025, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Attendance Amendment", {
    refresh(frm) {
        frm.events.set_year_and_month(frm);
        frm.events.filter_site_by_project(frm);
        toggle_day_value_fields_in_attendance_details(frm);

        if (!frm.is_new() && frm.doc.workflow_state !== "Cancelled") {
            // Story 1: Standalone "Preview Attendance" button (no group)
            frm.add_custom_button(__("Preview Attendance"), function() {
                show_attendance_preview_modal(frm);
            });

            // Version Changes button
            frm.add_custom_button(__("Version Changes"), function() {
                show_version_changes(frm);
            });
        }

        if (!frm.is_new() && frm.doc.workflow_state === "Approved") {
            // Story 1: Standalone "Generate Invoice" button (no group)
            frm.add_custom_button(__("Generate Invoice"), function() {
                frappe.confirm(__("Generate Sales Invoice for this Attendance Amendment?"), function() {
                    frappe.call({
                        method: "one_fm.one_fm.doctype.attendance_amendment.attendance_invoicing.generate_invoice_from_amendment",
                        args: { amendment_name: frm.doc.name },
                        freeze: true,
                        freeze_message: __("Generating Sales Invoice..."),
                        callback: function(r) {
                            if (r.message) {
                                let names = r.message.split(",").map(n => n.trim()).filter(Boolean);
                                if (names.length === 1) {
                                    frappe.msgprint(__("Sales Invoice Generated: ") + names[0]);
                                    frappe.set_route("Form", "Sales Invoice", names[0]);
                                } else {
                                    let links = names.map(n =>
                                        `<a href="/app/sales-invoice/${encodeURIComponent(n)}">${n}</a>`
                                    ).join("<br>");
                                    frappe.msgprint({
                                        title: __("Sales Invoices Generated"),
                                        message: __("The following invoices were created:") + "<br>" + links,
                                        indicator: "green"
                                    });
                                }
                            }
                        }
                    });
                });
            }).addClass("btn-primary");
        }
    },
    fetch_attendance_record(frm){
        frappe.call({
            method: "fetch_attendance_record",
            doc: frm.doc,
            callback: function(r) {
                frm.refresh_fields();
                // trigger working days calc after fetch only for Attendance Status mode
                if (frm.doc.attendance_based_on === "Attendance Status") {
                    let items = frm.doc.attendance_details || [];
                    items.forEach(d => calculate_working_days(frm, d.doctype, d.name));
                }
            },
            freeze: true,
            freeze_message: "Fetching Attendance Records..."
        });
    },
    set_year_and_month(frm){
        if(frm.is_new()){
            var month_map = {
                1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June", 7: "July", 8: "August", 
                9: "September", 10: "October", 11: "November", 12: "December"
            }
            frm.set_value("year", frappe.datetime.get_today().substr(0,4));
            frm.set_value("month", month_map[frappe.datetime.str_to_obj(frappe.datetime.get_today()).getMonth() + 1]);
        }
    },
    project(frm) {
        frm.events.filter_site_by_project(frm);
        frm.set_value("attendance_details", []);
        frm.set_value("overtime_details", []);
        frm.set_value("site", "");

        if (frm.doc.project) {
            frappe.db.get_list("Contracts", {
                filters: { project: frm.doc.project},
                fields: ["name"],
                limit: 1
            }).then(records => {
                if (records && records.length > 0) {
                    frm.set_value("contract", records[0].name);
                } else {
                    frm.set_value("contract", "");
                }
            });
        } else {
            frm.set_value("contract", "");
        }
    },
    year(frm){
        frm.set_value("attendance_details", []);
        frm.set_value("overtime_details", []);
    },
    month(frm){
        frm.set_value("attendance_details", []);
        frm.set_value("overtime_details", []);
    },
    site(frm){
        frm.set_value("attendance_details", []);
        frm.set_value("overtime_details", []);
    },
    attendance_based_on(frm){
        frm.set_value("attendance_details", []);
        frm.set_value("overtime_details", []);
        toggle_day_value_fields_in_attendance_details(frm);
    },
    filter_site_by_project(frm){
        // Filter Site field by selected Project
        if(frm.doc.project){
            frm.set_query("site", function() {
                return {
                    filters: {
                        project: frm.doc.project || undefined
                    }
                };
            });
        }
    }
});

function toggle_day_value_fields_in_attendance_details(frm){
    // The child table JSONs have depends_on set on their section breaks
    // which reference parent.attendance_based_on. We just need to refresh
    // the grids so Frappe re-evaluates those depends_on expressions.
    if (frm.fields_dict.attendance_details && frm.fields_dict.attendance_details.grid) {
        frm.fields_dict.attendance_details.grid.refresh();
    }
    if (frm.fields_dict.overtime_details && frm.fields_dict.overtime_details.grid) {
        frm.fields_dict.overtime_details.grid.refresh();
    }
}

function calculate_working_days(frm, cdt, cdn) {
    let row = frappe.get_doc(cdt, cdn);
    let working_days = 0;
    let off_days = 0;
    
    for (let i = 1; i <= 31; i++) {
        if (frm.doc.attendance_based_on === "Attendance Status") {
            let val = row['day_' + i];
            if (val && ["Present", "Working", "Work From Home", "Half Day"].includes(val)) {
                working_days += (val === "Half Day" ? 0.5 : 1);
            } else if (val && ["Day Off", "Client Day Off"].includes(val)) {
                off_days += 1;
            }
        } else if (["Shift Hours", "Working Hours"].includes(frm.doc.attendance_based_on)) {
            let val = row['day_' + i];
            let hour_val = row['day_' + i + '_hour'];
            if (val && ["Day Off", "Client Day Off"].includes(val)) {
                off_days += 1;
            } else if (hour_val && hour_val !== 'N/A') {
                let h = Number(hour_val) || 0;
                if (h > 0) working_days += 1;
            }
        }
    }
    frappe.model.set_value(cdt, cdn, "working_days", working_days);
    frappe.model.set_value(cdt, cdn, "off_days", off_days);
}

let child_events = {};
for (let i = 1; i <= 31; i++) {
    child_events['day_' + i] = function(frm, cdt, cdn) {
        calculate_working_days(frm, cdt, cdn);
    };
    child_events['day_' + i + '_hour'] = function(frm, cdt, cdn) {
        calculate_working_days(frm, cdt, cdn);
    };
}
frappe.ui.form.on("Attendance Amendment Item", child_events);
frappe.ui.form.on("Attendance Amendment OT Item", child_events);

// ============================================================
// Story 1 + 6: Attendance Preview Modal
// - 95% width modal (matching Subcontract Staff Attendance)
// - PDF export via print in new tab
// - Grouped by Sale Item with Item Type column and subtotals
// ============================================================

function show_attendance_preview_modal(frm) {
    let items = frm.doc.attendance_details || [];
    let ot_items = frm.doc.overtime_details || [];
    if (!items.length && !ot_items.length) {
        frappe.msgprint(__("No attendance details to preview."));
        return;
    }

    const month_map_array = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    let month_idx = month_map_array.indexOf(frm.doc.month);
    if (month_idx === -1) return;
    
    let year = parseInt(frm.doc.year);
    let days_in_month = new Date(year, month_idx + 1, 0).getDate();

    // Fetch item_type for each sale_item to display "Item Type" column
    frappe.call({
        method: "one_fm.one_fm.doctype.attendance_amendment.attendance_amendment.get_sale_item_details",
        args: { amendment_name: frm.doc.name },
        async: false,
        callback: function(r) {
            let item_type_map = r.message || {};
            render_grouped_preview(frm, items, ot_items, year, month_idx, days_in_month, item_type_map);
        }
    });
}

function render_grouped_preview(frm, items, ot_items, year, month_idx, days_in_month, item_type_map) {
    const is_hours_mode = ["Shift Hours", "Working Hours"].includes(frm.doc.attendance_based_on);

    const status_map = {
        "Present": "P", "Absent": "A", "On Leave": "L", "Half Day": "HD",
        "Work From Home": "WFH", "Day Off": "DO", "Client Day Off": "CDO",
        "Fingerprint Appointment": "FA", "Medical Appointment": "MA",
        "Holiday": "H", "On Hold": "OH"
    };

    const format_num = (v, decimals) => {
        let n = Number(v);
        if (isNaN(n)) return String(v || 0);
        return decimals !== undefined ? n.toFixed(decimals) : String(n);
    };

    // ---- Group rows by sale_item ----
    let groups = {};
    let group_order = [];

    for (let row of items) {
        let key = row.sale_item || __("(No Sale Item)");
        if (!groups[key]) {
            groups[key] = [];
            group_order.push(key);
        }
        groups[key].push(row);
    }

    // ---- Build HTML for each group ----
    let full_html = "";

    // Attendance abbreviation legend
    full_html += `<div style="margin-bottom: 12px; padding: 8px 12px; background: #f8f9fa; border-radius: 6px; font-size: 11px; border: 1px solid #e2e8f0;">
        <strong>${__("Legend")}:</strong>
        P = ${__("Present")}, A = ${__("Absent")}, L = ${__("On Leave")}, HD = ${__("Half Day")},
        WFH = ${__("Work From Home")}, DO = ${__("Day Off")}, CDO = ${__("Client Day Off")},
        FA = ${__("Fingerprint Appt")}, MA = ${__("Medical Appt")}, H = ${__("Holiday")}, OH = ${__("On Hold")}
    </div>`;

    for (let sale_item of group_order) {
        let group_rows = groups[sale_item];

        // Section heading + table wrapped together so header aligns with table width
        let table_html = `<div style="overflow-x: auto; margin-bottom: 16px;">
        <div class="group-header-bar" style="margin-top: 16px; margin-bottom: 8px; padding: 6px 12px; background: #EBEBEB; color: #333; border-radius: 6px; font-size: 13px; display: table; width: 100%;">
            <strong>${__("Sale Item")}:</strong> ${frappe.utils.escape_html(sale_item)}
            <span style="float: right; opacity: 0.85;">${group_rows.length} ${__("employee(s)")}</span>
        </div>
        <table class="table table-bordered table-sm" style="font-size: 11px; text-align: center; border-collapse: collapse; white-space: nowrap; width: 100%;">`;

        // Header Row 1: Day names
        table_html += `<thead><tr style="background: #edf2f7;">`;
        table_html += `<th rowspan="2" style="vertical-align: middle; min-width: 110px; text-align: left;">${__("Item Type")}</th>`;
        table_html += `<th rowspan="2" style="vertical-align: middle; min-width: 70px;">${__("Employee ID")}</th>`;
        table_html += `<th rowspan="2" style="vertical-align: middle; min-width: 130px; text-align: left;">${__("Employee Name")}</th>`;

        for (let i = 1; i <= days_in_month; i++) {
            let d = new Date(year, month_idx, i);
            let day_name = d.toLocaleDateString('en-US', { weekday: 'short' });
            let is_friday = d.getDay() === 5;
            let bg = is_friday ? '#e2e8f0' : '';
            table_html += `<th style="background-color: ${bg}; min-width: 32px;">${day_name}</th>`;
        }

        table_html += `<th rowspan="2" style="vertical-align: middle; min-width: 70px;">${__("Working Days")}</th>`;
        table_html += `<th rowspan="2" style="vertical-align: middle; min-width: 60px;">${__("Days Off")}</th>`;
        if (is_hours_mode) {
            table_html += `<th rowspan="2" style="vertical-align: middle; min-width: 70px;">${__("Total Hours")}</th>`;
        }
        table_html += `</tr>`;

        // Header Row 2: Dates
        table_html += `<tr style="background: #edf2f7;">`;
        let m_display = month_idx + 1;
        for (let i = 1; i <= days_in_month; i++) {
            let d = new Date(year, month_idx, i);
            let is_friday = d.getDay() === 5;
            let bg = is_friday ? '#e2e8f0' : '';
            table_html += `<th style="background-color: ${bg}">${i}/${m_display}</th>`;
        }
        table_html += `</tr></thead><tbody>`;

        // Totals for this group
        let group_total_working = 0;
        let group_total_off = 0;
        let group_total_hours = 0;
        let day_col_totals = new Array(days_in_month + 1).fill(0);

        // Data rows
        for (let row of group_rows) {
            let item_type = item_type_map[row.sale_item] || "";

            table_html += `<tr>`;
            table_html += `<td style="text-align: left; font-size: 10px;">${frappe.utils.escape_html(item_type)}</td>`;
            table_html += `<td>${row.employee_id || ''}</td>`;
            table_html += `<td style="text-align: left;">${row.employee_name || ''}</td>`;

            let working_total = 0;
            let days_off = 0;
            let hours_total = 0;

            for (let i = 1; i <= days_in_month; i++) {
                let d = new Date(year, month_idx, i);
                let is_friday = d.getDay() === 5;
                let bg = is_friday ? '#f1f5f9' : '';
                let status_val = row['day_' + i] || '';
                let hour_val = row['day_' + i + '_hour'];
                let val_short = '';

                if (is_hours_mode) {
                    // Resolve effective status from day_X or day_X_hour (for old data with status in hour field)
                    let eff_status = status_val || '';
                    let has_numeric_hour = (hour_val !== undefined && hour_val !== null && hour_val !== '' && !isNaN(Number(hour_val)));
                    let is_hour_a_status = (hour_val && isNaN(Number(hour_val)) && String(hour_val) !== 'N/A');
                    if (!eff_status && is_hour_a_status) eff_status = String(hour_val);

                    // Priority 1: Numeric hour value takes precedence over default Select value
                    if (has_numeric_hour) {
                        val_short = format_num(hour_val, 2);
                        let h = Number(hour_val) || 0;
                        hours_total += h;
                        if (h > 0) working_total++;
                    // Priority 2: Day off statuses
                    } else if (eff_status === "Day Off" || eff_status === "Client Day Off") {
                        val_short = status_map[eff_status] || eff_status;
                        days_off++;
                    // Priority 3: Other known statuses (On Leave, Absent, etc.)
                    } else if (status_map[eff_status] && eff_status !== "Present") {
                        val_short = status_map[eff_status];
                        if (eff_status === "Half Day") working_total += 0.5;
                        else if (eff_status === "Working" || eff_status === "Work From Home") working_total++;
                    } else if (eff_status && eff_status !== "Present") {
                        val_short = eff_status;
                    }
                } else {
                    val_short = status_map[status_val] || status_val;

                    if (status_val === "Present" || status_val === "Working" || status_val === "Work From Home") {
                        working_total++;
                    } else if (status_val === "Half Day") {
                        working_total += 0.5;
                    } else if (status_val === "Day Off" || status_val === "Client Day Off") {
                        days_off++;
                    }
                }

                if (is_hours_mode) {
                    let h = Number(hour_val) || 0;
                    day_col_totals[i] += h;
                }
                table_html += `<td style="background-color: ${bg}">${val_short}</td>`;
            }

            group_total_working += working_total;
            group_total_off += days_off;
            group_total_hours += hours_total;

            table_html += `<td><strong>${is_hours_mode ? format_num(working_total, 2) : format_num(working_total)}</strong></td>`;
            table_html += `<td><strong>${days_off}</strong></td>`;
            if (is_hours_mode) {
                table_html += `<td><strong>${format_num(hours_total, 2)}</strong></td>`;
            }
            table_html += `</tr>`;
        }

        // Subtotal row with per-day column sums
        table_html += `<tr style="background: #EBEBEB; font-weight: bold; border-top: 2px solid #999;">`;
        table_html += `<td colspan="3" style="text-align: right; padding-right: 8px;">
            ${__("Total")}: ${group_rows.length} ${__("employee(s)")}
        </td>`;
        for (let i = 1; i <= days_in_month; i++) {
            if (is_hours_mode && day_col_totals[i] > 0) {
                table_html += `<td>${format_num(day_col_totals[i], 2)}</td>`;
            } else {
                table_html += `<td></td>`;
            }
        }
        table_html += `<td>${is_hours_mode ? format_num(group_total_working, 2) : format_num(group_total_working)}</td>`;
        table_html += `<td>${group_total_off}</td>`;
        if (is_hours_mode) {
            table_html += `<td>${format_num(group_total_hours, 2)}</td>`;
        }
        table_html += `</tr>`;

        table_html += `</tbody></table></div>`;
        full_html += table_html;
    }

    // ============================================================
    // Overtime Details Section
    // ============================================================
    if (ot_items && ot_items.length > 0) {
        full_html += `<div style="margin-top: 28px; margin-bottom: 12px; padding: 8px 14px; background: #EBEBEB; color: #333; border-radius: 6px; font-size: 15px; font-weight: bold;">
            <i class="fa fa-clock-o" style="margin-right: 6px;"></i>${__("Overtime Details")}
        </div>`;

        // Group OT rows by sale_item
        let ot_groups = {};
        let ot_group_order = [];
        for (let row of ot_items) {
            let key = row.sale_item || __("(No Sale Item)");
            if (!ot_groups[key]) {
                ot_groups[key] = [];
                ot_group_order.push(key);
            }
            ot_groups[key].push(row);
        }

        for (let sale_item of ot_group_order) {
            let group_rows = ot_groups[sale_item];

            // Section heading + table wrapped together
            let table_html = `<div style="overflow-x: auto; margin-bottom: 16px;">
            <div class="group-header-bar" style="margin-top: 12px; margin-bottom: 8px; padding: 6px 12px; background: #EBEBEB; color: #333; border-radius: 6px; font-size: 13px; display: table; width: 100%;">
                <strong>${__("Sale Item")}:</strong> ${frappe.utils.escape_html(sale_item)}
                <span style="float: right; opacity: 0.85;">${group_rows.length} ${__("employee(s)")}</span>
            </div>
            <table class="table table-bordered table-sm" style="font-size: 11px; text-align: center; border-collapse: collapse; white-space: nowrap; width: 100%;">`;

            // Header Row 1: Day names
            table_html += `<thead><tr style="background: #fff5f5;">`;
            table_html += `<th rowspan="2" style="vertical-align: middle; min-width: 110px; text-align: left;">${__("Item Type")}</th>`;
            table_html += `<th rowspan="2" style="vertical-align: middle; min-width: 70px;">${__("Employee ID")}</th>`;
            table_html += `<th rowspan="2" style="vertical-align: middle; min-width: 130px; text-align: left;">${__("Employee Name")}</th>`;

            for (let i = 1; i <= days_in_month; i++) {
                let d = new Date(year, month_idx, i);
                let day_name = d.toLocaleDateString('en-US', { weekday: 'short' });
                let is_friday = d.getDay() === 5;
                let bg = is_friday ? '#feebc8' : '';
                table_html += `<th style="background-color: ${bg}; min-width: 32px;">${day_name}</th>`;
            }

            table_html += `<th rowspan="2" style="vertical-align: middle; min-width: 70px;">${__("Working Days")}</th>`;
            table_html += `<th rowspan="2" style="vertical-align: middle; min-width: 60px;">${__("Days Off")}</th>`;
            if (is_hours_mode) {
                table_html += `<th rowspan="2" style="vertical-align: middle; min-width: 70px;">${__("Total Hours")}</th>`;
            }
            table_html += `</tr>`;

            // Header Row 2: Dates
            table_html += `<tr style="background: #fff5f5;">`;
            let m_display = month_idx + 1;
            for (let i = 1; i <= days_in_month; i++) {
                let d = new Date(year, month_idx, i);
                let is_friday = d.getDay() === 5;
                let bg = is_friday ? '#feebc8' : '';
                table_html += `<th style="background-color: ${bg}">${i}/${m_display}</th>`;
            }
            table_html += `</tr></thead><tbody>`;

            let group_total_working = 0;
            let group_total_off = 0;
            let group_total_hours = 0;
            let ot_day_col_totals = new Array(days_in_month + 1).fill(0);

            for (let row of group_rows) {
                let item_type = item_type_map[row.sale_item] || "";

                table_html += `<tr>`;
                table_html += `<td style="text-align: left; font-size: 10px;">${frappe.utils.escape_html(item_type)}</td>`;
                table_html += `<td>${row.employee_id || ''}</td>`;
                table_html += `<td style="text-align: left;">${row.employee_name || ''}</td>`;

                let working_total = 0;
                let days_off = 0;
                let hours_total = 0;

                for (let i = 1; i <= days_in_month; i++) {
                    let d = new Date(year, month_idx, i);
                    let is_friday = d.getDay() === 5;
                    let bg = is_friday ? '#fffaf0' : '';
                    let status_val = row['day_' + i] || '';
                    let hour_val = row['day_' + i + '_hour'];
                    let val_short = '';

                    if (is_hours_mode) {
                        let eff_status = status_val || '';
                        let has_numeric_hour = (hour_val !== undefined && hour_val !== null && hour_val !== '' && !isNaN(Number(hour_val)));
                        let is_hour_a_status = (hour_val && isNaN(Number(hour_val)) && String(hour_val) !== 'N/A');
                        if (!eff_status && is_hour_a_status) eff_status = String(hour_val);

                        if (has_numeric_hour) {
                            val_short = format_num(hour_val, 2);
                            let h = Number(hour_val) || 0;
                            hours_total += h;
                            if (h > 0) working_total++;
                        } else if (eff_status === "Day Off" || eff_status === "Client Day Off") {
                            val_short = status_map[eff_status] || eff_status;
                            days_off++;
                        } else if (status_map[eff_status] && eff_status !== "Present") {
                            val_short = status_map[eff_status];
                            if (eff_status === "Half Day") working_total += 0.5;
                            else if (eff_status === "Working" || eff_status === "Work From Home") working_total++;
                        } else if (eff_status && eff_status !== "Present") {
                            val_short = eff_status;
                        }
                    } else {
                        val_short = status_map[status_val] || status_val;

                        if (status_val === "Present" || status_val === "Working" || status_val === "Work From Home") {
                            working_total++;
                        } else if (status_val === "Half Day") {
                            working_total += 0.5;
                        } else if (status_val === "Day Off" || status_val === "Client Day Off") {
                            days_off++;
                        }
                    }

                    if (is_hours_mode) {
                        let h = Number(hour_val) || 0;
                        ot_day_col_totals[i] += h;
                    }
                    table_html += `<td style="background-color: ${bg}">${val_short}</td>`;
                }

                group_total_working += working_total;
                group_total_off += days_off;
                group_total_hours += hours_total;

                table_html += `<td><strong>${is_hours_mode ? format_num(working_total, 2) : format_num(working_total)}</strong></td>`;
                table_html += `<td><strong>${days_off}</strong></td>`;
                if (is_hours_mode) {
                    table_html += `<td><strong>${format_num(hours_total, 2)}</strong></td>`;
                }
                table_html += `</tr>`;
            }

            // Subtotal row with per-day column sums
            table_html += `<tr style="background: #EBEBEB; font-weight: bold; border-top: 2px solid #999;">`;
            table_html += `<td colspan="3" style="text-align: right; padding-right: 8px;">
                ${__("Total")}: ${group_rows.length} ${__("employee(s)")}
            </td>`;
            for (let i = 1; i <= days_in_month; i++) {
                if (is_hours_mode && ot_day_col_totals[i] > 0) {
                    table_html += `<td>${format_num(ot_day_col_totals[i], 2)}</td>`;
                } else {
                    table_html += `<td></td>`;
                }
            }
            table_html += `<td>${is_hours_mode ? format_num(group_total_working, 2) : format_num(group_total_working)}</td>`;
            table_html += `<td>${group_total_off}</td>`;
            if (is_hours_mode) {
                table_html += `<td>${format_num(group_total_hours, 2)}</td>`;
            }
            table_html += `</tr>`;

            table_html += `</tbody></table></div>`;
            full_html += table_html;
        }
    }

    // ---- Create dialog ----
    let dialog = new frappe.ui.Dialog({
        title: __("Attendance Preview"),
        size: "extra-large",
        fields: [
            {
                fieldname: "preview_html",
                fieldtype: "HTML"
            }
        ]
    });

    dialog.fields_dict.preview_html.$wrapper.html(full_html);

    // Story 1: 95% modal width (matching Subcontract Staff Attendance)
    dialog.$wrapper.find('.modal-dialog').css('max-width', '95%');

    // Story 1: PDF Export button in dialog header
    let $pdf_btn = $(`<button class="btn btn-xs btn-default" title="${__("Export as PDF")}" style="margin-left: 8px;">
        <i class="fa fa-file-pdf-o"></i> ${__("PDF")}
    </button>`);

    $pdf_btn.on('click', function() {
        export_preview_as_pdf(full_html, frm);
    });

    dialog.$wrapper.find('.modal-header .modal-title').after($pdf_btn);

    dialog.show();
}

function export_preview_as_pdf(html_content, frm) {
    let title = `${__("Attendance Preview")} - ${frm.doc.project || ''} - ${frm.doc.month} ${frm.doc.year}`;

    // Fetch metadata via server call to avoid client-side Promise [object Object] issues
    frappe.call({
        method: "one_fm.one_fm.doctype.attendance_amendment.attendance_amendment.get_pdf_header_metadata",
        args: { amendment_name: frm.doc.name },
        async: false,
        callback: function(r) {
            if (!r.message) return;
            let meta = r.message;
            let logo_url = meta.logo_url || "";
            // Convert relative path to absolute URL so it works in Blob-based PDF
            if (logo_url && !logo_url.startsWith("http")) {
                logo_url = window.location.origin + (logo_url.startsWith("/") ? "" : "/") + logo_url;
            }
            let company_name = meta.company_name || "";
            let client_name = meta.client_name || "";
            let project_name = meta.project_name || "";
            let period_str = `${frm.doc.month} ${frm.doc.year}`;

            let header_html = `<div style="margin-bottom: 12px; padding: 10px 14px; background: #EBEBEB; border-radius: 6px; font-size: 11px; display: flex; align-items: flex-start; gap: 40px;">`;
            if (logo_url) {
                header_html += `<img src="${logo_url}" style="max-height: 50px; max-width: 120px;" />`;
            }
            header_html += `<div>
                <table style="border: none; font-size: 11px; border-collapse: collapse; text-align: left;">
                    <tr><td style="border: none; padding: 1px 12px 1px 0; font-weight: bold; text-align: left; white-space: nowrap;">${__("Project")}:</td><td style="border: none; padding: 1px 0; text-align: left;">${frappe.utils.escape_html(project_name)}</td></tr>
                    <tr><td style="border: none; padding: 1px 12px 1px 0; font-weight: bold; text-align: left; white-space: nowrap;">${__("Company")}:</td><td style="border: none; padding: 1px 0; text-align: left;">${frappe.utils.escape_html(company_name)}</td></tr>
                    <tr><td style="border: none; padding: 1px 12px 1px 0; font-weight: bold; text-align: left; white-space: nowrap;">${__("Client")}:</td><td style="border: none; padding: 1px 0; text-align: left;">${frappe.utils.escape_html(client_name)}</td></tr>
                    <tr><td style="border: none; padding: 1px 12px 1px 0; font-weight: bold; text-align: left; white-space: nowrap;">${__("Report Period")}:</td><td style="border: none; padding: 1px 0; text-align: left;">${frappe.utils.escape_html(period_str)}</td></tr>
                </table>
            </div></div>`;

            let print_html = `<!DOCTYPE html>
<html>
<head>
    <title>${title}</title>
    <style>
        @page { size: landscape; margin: 5mm; }
        * { box-sizing: border-box; }
        body { font-family: Arial, Helvetica, sans-serif; font-size: 9px; margin: 0; padding: 5px; }
        table { border-collapse: collapse; margin-bottom: 8px; page-break-inside: auto; width: 100%; }
        thead { display: table-header-group; }
        tr { page-break-inside: avoid; }
        th, td { border: 1px solid #bbb; padding: 2px 3px; text-align: center; font-size: 8px; white-space: nowrap; }
        th { background: #EBEBEB; font-weight: bold; }
        strong { font-weight: bold; }
        div[style*="overflow-x"] { overflow: visible !important; }
        .group-header-bar { display: table; width: 100%; page-break-after: avoid; }
        .group-section { page-break-inside: auto; }
        @media print { button { display: none !important; } body { -webkit-print-color-adjust: exact; print-color-adjust: exact; } }
    </style>
</head>
<body>
    <div id="content-wrapper">
        ${header_html}
        ${html_content}
    </div>
    <script>
        window.onload = function() {
            var wrapper = document.getElementById('content-wrapper');
            var pageWidth = 1085;
            // Scan all tables to find the true max content width
            var tables = document.querySelectorAll('table');
            var maxWidth = wrapper.scrollWidth;
            for (var i = 0; i < tables.length; i++) {
                if (tables[i].scrollWidth > maxWidth) maxWidth = tables[i].scrollWidth;
            }
            if (maxWidth > pageWidth) {
                var scale = pageWidth / maxWidth;
                document.body.style.zoom = scale;
            }
            setTimeout(function() { window.print(); }, 300);
        };
    </script>
</body>
</html>`;

            let blob = new Blob([print_html], { type: 'text/html' });
            let url = URL.createObjectURL(blob);
            window.open(url, '_blank');
        }
    });
}

// ============================================================
// Version Changes Dialog
// Shows document change history with who, when, and what changed
// ============================================================

function show_version_changes(frm) {
    frappe.call({
        method: "one_fm.one_fm.doctype.attendance_amendment.attendance_amendment.get_version_changes",
        args: { amendment_name: frm.doc.name },
        freeze: true,
        freeze_message: __("Loading version history..."),
        callback: function(r) {
            if (!r.message || r.message.length === 0) {
                frappe.msgprint(__("No version changes found for this document."));
                return;
            }
            render_version_changes_dialog(frm, r.message);
        }
    });
}

function render_version_changes_dialog(frm, versions) {
    let html = "";

    // Helper to format field names to human-readable labels
    const format_field_label = (fieldname) => {
        return fieldname
            .replace(/_/g, " ")
            .replace(/\b\w/g, c => c.toUpperCase());
    };

    // Helper to truncate long values
    const truncate = (val, max_len) => {
        if (!val) return '<span class="text-muted">-</span>';
        let s = String(val);
        if (s.length > (max_len || 80)) {
            return frappe.utils.escape_html(s.substring(0, max_len || 80)) + "…";
        }
        return frappe.utils.escape_html(s);
    };

    for (let i = 0; i < versions.length; i++) {
        let v = versions[i];
        let datetime_str = frappe.datetime.str_to_user(v.modified_on);
        let user_avatar = frappe.avatar(v.modified_by, "avatar-small");

        html += `<div class="version-entry mb-4 pb-3" style="border-bottom: 1px solid var(--border-color);">`;

        // Header: avatar, name, datetime
        html += `<div class="d-flex align-items-center mb-2">
            ${user_avatar}
            <div class="ml-2">
                <span class="font-weight-bold">${frappe.utils.escape_html(v.full_name)}</span>
                <br>
                <span class="text-muted small">${datetime_str}</span>
            </div>
        </div>`;

        // Field-level changes
        if (v.changes && v.changes.length > 0) {
            html += `<div class="mb-2">
                <div class="text-muted small font-weight-bold mb-1">${__("Field Changes")}</div>
                <table class="table table-sm table-borderless" style="font-size: 12px;">
                    <thead>
                        <tr class="text-muted">
                            <th style="width: 30%;">${__("Field")}</th>
                            <th style="width: 35%;">${__("Previous Value")}</th>
                            <th style="width: 35%;">${__("Current Value")}</th>
                        </tr>
                    </thead>
                    <tbody>`;

            for (let c of v.changes) {
                html += `<tr>
                    <td class="font-weight-bold">${format_field_label(c.field)}</td>
                    <td style="color: var(--red-500);">${truncate(c.old_value, 120)}</td>
                    <td style="color: var(--green-600);">${truncate(c.new_value, 120)}</td>
                </tr>`;
            }

            html += `</tbody></table></div>`;
        }

        // Child table row changes
        if (v.row_changes && v.row_changes.length > 0) {
            html += `<div class="mb-2">
                <div class="text-muted small font-weight-bold mb-1">${__("Row Changes")}</div>`;

            for (let rc of v.row_changes) {
                let table_label = format_field_label(rc.table);
                html += `<div class="ml-2 mb-2">
                    <span class="small"><strong>${table_label}</strong> — ${__("Row")} ${rc.row_index + 1}</span>
                    <table class="table table-sm table-borderless ml-2" style="font-size: 12px;">
                        <thead>
                            <tr class="text-muted">
                                <th style="width: 30%;">${__("Field")}</th>
                                <th style="width: 35%;">${__("Previous Value")}</th>
                                <th style="width: 35%;">${__("Current Value")}</th>
                            </tr>
                        </thead>
                        <tbody>`;

                for (let fc of rc.changes) {
                    html += `<tr>
                        <td class="font-weight-bold">${format_field_label(fc.field)}</td>
                        <td style="color: var(--red-500);">${truncate(fc.old_value, 80)}</td>
                        <td style="color: var(--green-600);">${truncate(fc.new_value, 80)}</td>
                    </tr>`;
                }

                html += `</tbody></table></div>`;
            }
            html += `</div>`;
        }

        // Added rows
        if (v.added_rows && v.added_rows.length > 0) {
            html += `<div class="mb-2">
                <div class="text-muted small font-weight-bold mb-1">
                    <span style="color: var(--green-600);">+ ${v.added_rows.length} ${__("row(s) added")}</span>
                </div>`;

            for (let ar of v.added_rows) {
                let table_label = format_field_label(ar.table);
                let summary_parts = [];
                if (ar.row_data.employee_name) {
                    summary_parts.push(ar.row_data.employee_name);
                }
                if (ar.row_data.employee_id) {
                    summary_parts.push(ar.row_data.employee_id);
                }
                let summary = summary_parts.length > 0
                    ? summary_parts.join(" — ")
                    : __("New row");
                html += `<div class="ml-2 small">
                    <strong>${table_label}</strong>: ${frappe.utils.escape_html(summary)}
                </div>`;
            }
            html += `</div>`;
        }

        // Removed rows
        if (v.removed_rows && v.removed_rows.length > 0) {
            html += `<div class="mb-2">
                <div class="text-muted small font-weight-bold mb-1">
                    <span style="color: var(--red-500);">− ${v.removed_rows.length} ${__("row(s) removed")}</span>
                </div>`;

            for (let rr of v.removed_rows) {
                let table_label = format_field_label(rr.table);
                let summary_parts = [];
                if (rr.row_data.employee_name) {
                    summary_parts.push(rr.row_data.employee_name);
                }
                if (rr.row_data.employee_id) {
                    summary_parts.push(rr.row_data.employee_id);
                }
                let summary = summary_parts.length > 0
                    ? summary_parts.join(" — ")
                    : __("Removed row");
                html += `<div class="ml-2 small">
                    <strong>${table_label}</strong>: ${frappe.utils.escape_html(summary)}
                </div>`;
            }
            html += `</div>`;
        }

        html += `</div>`;  // close version-entry
    }

    let dialog = new frappe.ui.Dialog({
        title: __("Version Changes") + " — " + frm.doc.name,
        size: "large",
        fields: [
            {
                fieldname: "version_html",
                fieldtype: "HTML"
            }
        ]
    });

    dialog.fields_dict.version_html.$wrapper.html(
        `<div style="max-height: 500px; overflow-y: auto; padding: 8px;">${html}</div>`
    );

    dialog.show();
}