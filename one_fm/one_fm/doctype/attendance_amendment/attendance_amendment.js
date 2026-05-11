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
        let val = row['day_' + i];
        if (frm.doc.attendance_based_on === "Attendance Status") {
            if (val && ["Present", "Working", "Work From Home", "Half Day"].includes(val)) {
                working_days += (val === "Half Day" ? 0.5 : 1);
            } else if (val && ["Day Off", "Client Day Off"].includes(val)) {
                off_days += 1;
            }
        }
    }
    frappe.model.set_value(cdt, cdn, "working_days", working_days);
    frappe.model.set_value(cdt, cdn, "off_days", off_days);
}

let child_events = {};
for (let i = 1; i <= 31; i++) {
    child_events['day_' + i] = function(frm, cdt, cdn) {
        if (frm.doc.attendance_based_on === "Attendance Status") {
            calculate_working_days(frm, cdt, cdn);
        }
    };
}
frappe.ui.form.on("Attendance Amendment Item", child_events);
frappe.ui.form.on("Attendance Amendment OT Item", child_events);

// ============================================================
// Story 1 + 6: Attendance Preview Modal
// - 95% width modal (matching Subcontract Staff Attendance)
// - PDF export via print in new tab
// - Grouped by Sale Item with Role Name column and subtotals
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

    // Fetch role names from Operations Role to display "Role Name" column
    frappe.call({
        method: "one_fm.one_fm.doctype.attendance_amendment.attendance_amendment.get_operations_role_names",
        args: { amendment_name: frm.doc.name },
        async: false,
        callback: function(r) {
            let role_name_map = r.message || {};
            render_grouped_preview(frm, items, ot_items, year, month_idx, days_in_month, role_name_map);
        }
    });
}

function render_grouped_preview(frm, items, ot_items, year, month_idx, days_in_month, role_name_map) {
    const is_shift_hours = frm.doc.attendance_based_on === "Shift Hours";

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

        // Section heading
        full_html += `<div style="margin-top: 16px; margin-bottom: 8px; padding: 6px 12px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #fff; border-radius: 6px; font-size: 13px;">
            <strong>${__("Sale Item")}:</strong> ${frappe.utils.escape_html(sale_item)}
            <span style="float: right; opacity: 0.85;">${group_rows.length} ${__("employee(s)")}</span>
        </div>`;

        // Build table
        let table_html = `<div style="overflow-x: auto; margin-bottom: 16px;">
        <table class="table table-bordered table-sm" style="font-size: 11px; text-align: center; border-collapse: collapse; white-space: nowrap;">`;

        // Header Row 1: Day names
        table_html += `<thead><tr style="background: #edf2f7;">`;
        table_html += `<th rowspan="2" style="vertical-align: middle; min-width: 110px; text-align: left;">${__("Role Name")}</th>`;
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
        if (is_shift_hours) {
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

        // Data rows
        for (let row of group_rows) {
            let role_name = role_name_map[row.operations_role] || "";
            let row_sale_item = row.sale_item || "";

            table_html += `<tr>`;
            table_html += `<td style="text-align: left; font-size: 10px;">${frappe.utils.escape_html(role_name)}</td>`;
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

                if (is_shift_hours) {
                    if (status_val === "Day Off") {
                        val_short = "DO";
                        days_off++;
                    } else if (status_val === "Client Day Off") {
                        val_short = "CDO";
                        days_off++;
                    } else if (hour_val !== undefined && hour_val !== null && hour_val !== "") {
                        val_short = format_num(hour_val, 2);
                        let h = Number(hour_val) || 0;
                        hours_total += h;
                        if (h > 0) working_total++;
                    } else if (status_val === "Absent") {
                        val_short = "A";
                    } else if (status_val === "Half Day") {
                        val_short = "HD";
                        working_total += 0.5;
                    } else if (status_val === "Present") {
                        val_short = "";
                    } else if (status_val === "Work From Home") {
                        val_short = "WFH";
                        working_total++;
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

                table_html += `<td style="background-color: ${bg}">${val_short}</td>`;
            }

            group_total_working += working_total;
            group_total_off += days_off;
            group_total_hours += hours_total;

            table_html += `<td><strong>${is_shift_hours ? format_num(working_total, 2) : format_num(working_total)}</strong></td>`;
            table_html += `<td><strong>${days_off}</strong></td>`;
            if (is_shift_hours) {
                table_html += `<td><strong>${format_num(hours_total, 2)}</strong></td>`;
            }
            table_html += `</tr>`;
        }

        // Subtotal row
        table_html += `<tr style="background: #edf2f7; font-weight: bold; border-top: 2px solid #667eea;">`;
        table_html += `<td colspan="3" style="text-align: right; padding-right: 8px;">
            ${__("Total")}: ${group_rows.length} ${__("employee(s)")}
        </td>`;
        for (let i = 1; i <= days_in_month; i++) {
            table_html += `<td></td>`;
        }
        table_html += `<td>${is_shift_hours ? format_num(group_total_working, 2) : format_num(group_total_working)}</td>`;
        table_html += `<td>${group_total_off}</td>`;
        if (is_shift_hours) {
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
        full_html += `<div style="margin-top: 28px; margin-bottom: 12px; padding: 8px 14px; background: linear-gradient(135deg, #e53e3e 0%, #dd6b20 100%); color: #fff; border-radius: 6px; font-size: 15px; font-weight: bold;">
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

            // Section heading
            full_html += `<div class="group-header-bar" style="margin-top: 12px; margin-bottom: 8px; padding: 6px 12px; background: linear-gradient(135deg, #e53e3e 0%, #dd6b20 100%); color: #fff; border-radius: 6px; font-size: 13px;">
                <strong>${__("Sale Item")}:</strong> ${frappe.utils.escape_html(sale_item)}
                <span style="float: right; opacity: 0.85;">${group_rows.length} ${__("employee(s)")}</span>
            </div>`;

            let table_html = `<div style="overflow-x: auto; margin-bottom: 16px;">
            <table class="table table-bordered table-sm" style="font-size: 11px; text-align: center; border-collapse: collapse; white-space: nowrap;">`;

            // Header Row 1: Day names
            table_html += `<thead><tr style="background: #fff5f5;">`;
            table_html += `<th rowspan="2" style="vertical-align: middle; min-width: 110px; text-align: left;">${__("Role Name")}</th>`;
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
            if (is_shift_hours) {
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

            for (let row of group_rows) {
                let role_name = role_name_map[row.operations_role] || "";

                table_html += `<tr>`;
                table_html += `<td style="text-align: left; font-size: 10px;">${frappe.utils.escape_html(role_name)}</td>`;
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

                    if (is_shift_hours) {
                        if (status_val === "Day Off") {
                            val_short = "DO";
                            days_off++;
                        } else if (status_val === "Client Day Off") {
                            val_short = "CDO";
                            days_off++;
                        } else if (hour_val !== undefined && hour_val !== null && hour_val !== "") {
                            val_short = format_num(hour_val, 2);
                            let h = Number(hour_val) || 0;
                            hours_total += h;
                            if (h > 0) working_total++;
                        } else if (status_val === "Absent") {
                            val_short = "A";
                        } else if (status_val === "Half Day") {
                            val_short = "HD";
                            working_total += 0.5;
                        } else if (status_val === "Work From Home") {
                            val_short = "WFH";
                            working_total++;
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

                    table_html += `<td style="background-color: ${bg}">${val_short}</td>`;
                }

                group_total_working += working_total;
                group_total_off += days_off;
                group_total_hours += hours_total;

                table_html += `<td><strong>${is_shift_hours ? format_num(working_total, 2) : format_num(working_total)}</strong></td>`;
                table_html += `<td><strong>${days_off}</strong></td>`;
                if (is_shift_hours) {
                    table_html += `<td><strong>${format_num(hours_total, 2)}</strong></td>`;
                }
                table_html += `</tr>`;
            }

            // Subtotal row
            table_html += `<tr style="background: #fff5f5; font-weight: bold; border-top: 2px solid #e53e3e;">`;
            table_html += `<td colspan="3" style="text-align: right; padding-right: 8px;">
                ${__("Total")}: ${group_rows.length} ${__("employee(s)")}
            </td>`;
            for (let i = 1; i <= days_in_month; i++) {
                table_html += `<td></td>`;
            }
            table_html += `<td>${is_shift_hours ? format_num(group_total_working, 2) : format_num(group_total_working)}</td>`;
            table_html += `<td>${group_total_off}</td>`;
            if (is_shift_hours) {
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

    let print_html = `<!DOCTYPE html>
<html>
<head>
    <title>${title}</title>
    <style>
        @page { size: landscape; margin: 5mm; }
        * { box-sizing: border-box; }
        body {
            font-family: Arial, Helvetica, sans-serif;
            font-size: 9px;
            margin: 0;
            padding: 5px;
        }
        h2 { font-size: 13px; margin-bottom: 6px; }
        table {
            border-collapse: collapse;
            margin-bottom: 8px;
            table-layout: auto;
            page-break-inside: auto;
        }
        thead { display: table-header-group; }
        tr { page-break-inside: avoid; }
        th, td {
            border: 1px solid #bbb;
            padding: 2px 3px;
            text-align: center;
            font-size: 8px;
            white-space: nowrap;
        }
        th { background: #edf2f7; font-weight: bold; }
        strong { font-weight: bold; }
        div[style*="overflow-x"] { overflow: visible !important; }
        .group-section { page-break-inside: auto; }
        .group-header-bar { page-break-after: avoid; }
        @media print {
            button { display: none !important; }
            body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
        }
    </style>
</head>
<body>
    <div id="content-wrapper">
        <h2>${title}</h2>
        ${html_content}
    </div>
    <script>
        window.onload = function() {
            // Use CSS zoom (not transform) so pagination works correctly.
            // transform:scale only changes visual rendering; zoom changes layout dimensions,
            // so the browser fills pages properly without gaps.
            var wrapper = document.getElementById('content-wrapper');
            var pageWidth = 1085; // Landscape A4 usable ≈ 287mm ≈ 1085px at 96dpi
            var contentWidth = wrapper.scrollWidth;
            if (contentWidth > pageWidth) {
                var scale = pageWidth / contentWidth;
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