// Copyright (c) 2025, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Attendance Amendment", {
    refresh(frm) {
        frm.events.set_year_and_month(frm);
        frm.events.filter_site_by_project(frm);
        toggle_day_value_fields_in_attendance_details(frm);

        if (!frm.is_new() && frm.doc.workflow_state !== "Cancelled") {
            frm.add_custom_button(__("Preview Attendance"), function() {
                show_attendance_preview_modal(frm);
            }, __("Actions"));
        }

        if (!frm.is_new() && frm.doc.workflow_state === "Approved") {
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
            }, __("Actions"));
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

function show_attendance_preview_modal(frm) {
    let items = frm.doc.attendance_details || [];
    if (!items.length) {
        frappe.msgprint(__("No attendance details to preview."));
        return;
    }

    const month_map_array = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    let month_idx = month_map_array.indexOf(frm.doc.month);
    if (month_idx === -1) return;
    
    let year = parseInt(frm.doc.year);
    let days_in_month = new Date(year, month_idx + 1, 0).getDate();

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

    let html = `<div style="overflow-x: auto;"><table class="table table-bordered table-sm" style="font-size: 12px; text-align: center; border-collapse: collapse;">`;
    
    // Header 1: Days of the week
    html += `<thead><tr>`;
    html += `<th rowspan="2" style="vertical-align: middle; min-width: 80px;">Employee ID</th>`;
    html += `<th rowspan="2" style="vertical-align: middle; min-width: 150px;">Employee Name</th>`;
    
    for (let i = 1; i <= days_in_month; i++) {
        let d = new Date(year, month_idx, i);
        let day_name = d.toLocaleDateString('en-US', { weekday: 'short' });
        let is_friday = d.getDay() === 5;
        let bg_color = is_friday ? '#e2e8f0' : '';
        html += `<th style="background-color: ${bg_color}">${day_name}</th>`;
    }
    html += `<th rowspan="2" style="vertical-align: middle; min-width: 80px;">Working Days</th>`;
    html += `<th rowspan="2" style="vertical-align: middle; min-width: 80px;">Days Off</th>`;
    html += `</tr>`;

    // Header 2: Dates (DD/MM)
    html += `<tr>`;
    let m_display = month_idx + 1;
    for (let i = 1; i <= days_in_month; i++) {
        let d = new Date(year, month_idx, i);
        let is_friday = d.getDay() === 5;
        let bg_color = is_friday ? '#e2e8f0' : '';
        html += `<th style="background-color: ${bg_color}">${i}/${m_display}</th>`;
    }
    html += `</tr></thead><tbody>`;

    const is_shift_hours = frm.doc.attendance_based_on === "Shift Hours";
    const format_preview_total = (value) => {
        let numeric_value = Number(value) || 0;
        return String(numeric_value);
    };

    for (let row of items) {
        html += `<tr>`;
        html += `<td>${row.employee_id || ''}</td>`;
        html += `<td style="text-align: left;">${row.employee_name || ''}</td>`;
        
        let working_total = 0;
        let days_off = 0;

        for (let i = 1; i <= days_in_month; i++) {
            let d = new Date(year, month_idx, i);
            let is_friday = d.getDay() === 5;
            let bg_color = is_friday ? '#f1f5f9' : '';
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
                    val_short = format_preview_total(hour_val);
                    working_total += Number(hour_val) || 0;
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
                let val = status_val;
                val_short = val;
                
                if (val === "Present") {
                    val_short = "P";
                    working_total++;
                } else if (val === "Absent") {
                    val_short = "A";
                } else if (val === "Work From Home") {
                    val_short = "WFH";
                    working_total++;
                } else if (val === "Half Day") {
                    val_short = "HD";
                    working_total += 0.5;
                } else if (val === "Day Off") {
                    val_short = "DO";
                    days_off++;
                } else if (val === "Client Day Off") {
                    val_short = "CDO";
                    days_off++;
                }
            }

            html += `<td style="background-color: ${bg_color}">${val_short}</td>`;
        }

        html += `<td><strong>${format_preview_total(working_total)}</strong></td>`;
        html += `<td><strong>${days_off}</strong></td>`;
        html += `</tr>`;
    }

    html += `</tbody></table></div>`;
    
    dialog.fields_dict.preview_html.$wrapper.html(html);
    dialog.show();
}