document.addEventListener("DOMContentLoaded", function() {
    const ctx = window.ATTENDANCE_CONTEXT || {};
    
    // Status maps for shorter display
    const status_maps = {
        "Present": "P", "Absent": "A", "On Leave": "L", "Half Day": "HD",
        "Work From Home": "WFH", "Day Off": "DO", "Client Day Off": "CDO",
        "Fingerprint Appointment": "FA", "Medical Appointment": "MA",
        "Holiday": "H", "On Hold": "OH"
    };

    const status_options = [
        "", "Present", "Absent", "On Leave", "Half Day", "Work From Home", 
        "Day Off", "Client Day Off", "Fingerprint Appointment", 
        "Medical Appointment", "Holiday", "On Hold"
    ];

    let grid_data = ctx.merged_data || [];
    let is_fetching = false;

    // Elements
    const btn_fetch = document.getElementById("btn-fetch");
    const btn_save = document.getElementById("btn-save");
    const btn_submit = document.getElementById("btn-submit");
    const input_from = document.getElementById("input-from-date");
    const input_to = document.getElementById("input-to-date");
    const input_based_on = document.getElementById("input-based-on");

    // Auto-populate To Date on From Date change
    if (input_from && input_to) {
        input_from.addEventListener("change", function() {
            if (this.value) {
                input_to.value = moment(this.value).endOf('month').format("YYYY-MM-DD");
            }
        });
    }
    
    // Grid rendering
    function render_grid(data) {
        if (!data || data.length === 0) {
            document.getElementById("matrix-table").style.display = "none";
            document.getElementById("empty-state").style.display = "block";
            return;
        }

        document.getElementById("matrix-table").style.display = "table";
        document.getElementById("empty-state").style.display = "none";

        const from_date = moment(input_from.value);
        const to_date = moment(input_to.value);
        const days_in_range = to_date.diff(from_date, 'days') + 1;
        const based_on = input_based_on.value;

        // Build Headers
        let header_days = `<th rowspan="2" class="name-col-header">Employee ID</th><th rowspan="2" class="name-col-header" style="z-index: 12 !important;">Employee Name</th>`;
        let header_dates = ``;
        let dates = [];

        for (let i = 0; i < days_in_range; i++) {
            let current_date = moment(from_date).add(i, 'days');
            let is_friday = current_date.day() === 5;
            dates.push({
                date: current_date, 
                is_friday: is_friday, 
                day_num: current_date.date(),
                idx: i + 1
            });
            
            header_days += `<th class="${is_friday ? 'bg-light' : ''}" style="min-width: 70px; text-align: center;">${current_date.format("ddd")}</th>`;
            header_dates += `<th class="${is_friday ? 'bg-light' : ''}" style="text-align: center;">${current_date.format("D/M")}</th>`;
        }
        
        header_days += `<th rowspan="2" class="calc-col">W. Days</th><th rowspan="2" class="calc-col">Off Days</th>`;

        document.getElementById("matrix-header-days").innerHTML = header_days;
        document.getElementById("matrix-header-dates").innerHTML = header_dates;

        // Build Body
        let body_html = "";
        let draft_employees = [];

        data.forEach((emp, rindex) => {
            let has_draft_cells = false;
            let cells_html = `<td class="name-col">${emp.employee_id}</td>
                              <td class="name-col" style="z-index: 10 !important; cursor: pointer; color: #0055cc;" onclick="window.open_row_detail('${emp.employee}')" title="Click to view details and remarks">
                                  <div class="d-flex justify-content-between align-items-center">
                                      <span>${emp.employee_name}</span>
                                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="opacity: 0.5"><path d="M15 3h6v6"></path><path d="M10 14L21 3"></path><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path></svg>
                                  </div>
                              </td>`;
            
            let w_days = 0;
            let o_days = 0;

            let remarks_html = "";
            let recorded_sites = new Set();
            let unique_remarks = new Set();

            dates.forEach(d => {
                let cell_data = (emp.days && emp.days[d.day_num]) || null;
                
                let is_locked = false;
                let is_draft = false;
                let value_display = "";
                let input_html = "";
                let class_name = d.is_friday ? "bg-light" : "";
                
                if (cell_data) {
                    recorded_sites.add(cell_data.site);
                    if (cell_data.remarks) unique_remarks.add(`[${cell_data.site}]: ${cell_data.remarks}`);

                    if (cell_data.status === "Pending Operations Supervisor" || cell_data.status === "Approved" || cell_data.status === "Pending Project Manager") {
                        is_locked = true;
                    } else if (cell_data.status === "Draft" && cell_data.remarks) {
                        is_draft = true;
                        has_draft_cells = true;
                    }

                    // Tally logic (same as backend calculations)
                    let tally_val = based_on === "Attendance Status" ? cell_data.value : cell_data.status_val;
                    if (based_on === "Shift Hours" && parseFloat(cell_data.value) > 0) w_days++;
                    else if (based_on === "Attendance Status" && ["Present", "Half Day", "Work From Home"].includes(tally_val)) w_days++;
                    
                    if (["Day Off", "Client Day Off"].includes(tally_val)) o_days++;

                }

                if (is_locked) {
                    let val = cell_data ? cell_data.value : "";
                    if (based_on === "Attendance Status") val = status_maps[val] || val;
                    class_name += " cell-locked";
                    
                    // Tooltip showing site
                    let tooltip = cell_data && cell_data.site ? `<div class="site-tooltip has-site">${cell_data.site}</div>` : "";
                    
                    let text_color_class = "";
                    if (val === "P") text_color_class = "status-Present";
                    else if (val === "A") text_color_class = "status-Absent";
                    
                    input_html = `<div class="cell-container"><span class="${text_color_class}">${val}</span>${tooltip}</div>`;
                } else {
                    if (is_draft) class_name += " cell-draft";
                    
                    let tooltip = cell_data && cell_data.site ? `<div class="site-tooltip has-site">${cell_data.site}</div>` : "";

                    if (based_on === "Attendance Status") {
                        let selected_val = cell_data ? cell_data.value : "";
                        let opts = status_options.map(opt => {
                            let disp = status_maps[opt] || opt;
                            return `<option value="${opt}" ${opt === selected_val ? 'selected' : ''}>${disp}</option>`;
                        }).join("");
                        
                        input_html = `<div class="cell-container">
                                        <select class="cell-input" data-emp="${emp.employee}" data-day="${d.day_num}">
                                            ${opts}
                                        </select>
                                        ${tooltip}
                                      </div>`;
                    } else {
                        let val = cell_data ? cell_data.value : "";
                        input_html = `<div class="cell-container">
                                        <input type="number" step="0.5" class="cell-input" style="min-width: 65px; padding: 4px 2px;" data-emp="${emp.employee}" data-day="${d.day_num}" value="${val}" />
                                        ${tooltip}
                                      </div>`;
                    }
                }

                cells_html += `<td class="${class_name}">${input_html}</td>`;
            });

            // Append Total Columns
            cells_html += `<td class="calc-col text-center font-weight-bold" id="wd-${emp.employee}">${w_days}</td>
                           <td class="calc-col text-center font-weight-bold text-danger" id="od-${emp.employee}">${o_days}</td>`;

            let tr_class = has_draft_cells ? "row-draft" : "";
            body_html += `<tr id="row-${rindex}" class="${tr_class}">${cells_html}</tr>`;
            if (has_draft_cells) {
                draft_employees.push(emp.employee_name);
            }
        });

        document.getElementById("matrix-body").innerHTML = body_html;

        // Attach event listeners for real-time calculation
        document.querySelectorAll(".cell-input").forEach(input => {
            input.addEventListener("change", function() {
                if (window.recalculate_row) {
                    window.recalculate_row(this.getAttribute("data-emp"));
                }
            });
        });

        // Define recalculate function
        window.recalculate_row = function(emp_id) {
            let based_on = input_based_on.value || ctx.based_on;
            let payload = collect_payload();
            let emp = payload.find(e => e.employee === emp_id);
            if (!emp || !emp.days) return;
            
            let w_days = 0;
            let o_days = 0;
            
            Object.values(emp.days).forEach(d_data => {
                let val = d_data.value;
                let tally_val = based_on === "Attendance Status" ? val : (d_data.status_val || "");
                
                if (based_on === "Shift Hours") {
                    if (parseFloat(val) > 0) w_days++;
                } else {
                    if (["Present", "Half Day", "Work From Home"].includes(val)) w_days++;
                }
                
                if (["Day Off", "Client Day Off"].includes(tally_val)) o_days++;
            });

            let wd_elem = document.getElementById(`wd-${emp_id}`);
            let od_elem = document.getElementById(`od-${emp_id}`);
            if (wd_elem) wd_elem.innerText = w_days;
            if (od_elem) od_elem.innerText = o_days;
        };

        // Render Alerts
        if (draft_employees.length > 0) {
            document.getElementById("alert-banner-container").innerHTML = `
                <div class="alert alert-danger" role="alert">
                    <h6 class="alert-heading font-weight-bold mb-1">⚠ Attention Required!</h6>
                    <p class="mb-0 small">The following employees have records that were returned to Draft for corrections: <strong>${draft_employees.join(", ")}</strong></p>
                </div>
            `;
        } else {
            document.getElementById("alert-banner-container").innerHTML = "";
        }

        // Render Legend
        let legend = document.getElementById("attendance-legend");
        if (legend) {
            legend.style.display = based_on === "Attendance Status" ? "block" : "none";
        }
    }

    // Read-only logic for Pending/Approved state
    if (ctx.compound_state && ctx.compound_state !== "Draft" && ctx.from_date) {
        if (input_from) input_from.disabled = true;
        if (input_to) input_to.disabled = true;
        if (input_based_on) input_based_on.disabled = true;
        if (btn_fetch) {
            btn_fetch.disabled = true;
            btn_fetch.style.display = "none";
        }
    }

    function validate_date_buffer(to_date_str) {
        if (!to_date_str) return true;
        let t_date = moment(to_date_str);
        let allowed_date = t_date.clone().add(1, 'months').date(11);
        let today = moment().startOf('day');
        
        if (today.isBefore(allowed_date, 'day')) {
            let msg = `You cannot select a billing month until the 11th of the following month. For ${t_date.format('MMMM YYYY')}, you must wait until ${allowed_date.format('MMMM D, YYYY')}.`;
            frappe.msgprint({title: "Validation Error", indicator: "red", message: msg});
            return false;
        }
        return true;
    }

    // Load initial data
    if (grid_data.length > 0) {
        render_grid(grid_data);
    }

    // Event: Fetch System Attendance
    if (btn_fetch) {
        btn_fetch.addEventListener("click", function() {
            if (!input_from.value || !input_to.value) {
                toastr.error("Please select From Date and To Date");
                return;
            }
            if (moment(input_to.value).isBefore(moment(input_from.value), 'day')) {
                toastr.error("To Date cannot be before From Date");
                return;
            }
            if (!validate_date_buffer(input_to.value)) {
                return;
            }
            if (is_fetching) return;
            
            btn_fetch.innerText = "Fetching...";
            is_fetching = true;

            frappe.call({
                method: "one_fm.one_fm.doctype.subcontract_staff_attendance.subcontract_staff_attendance.api_fetch_subcontractor_staff",
                args: {
                    subcontractor_name: ctx.supplier,
                    from_date: input_from.value,
                    to_date: input_to.value,
                    attendance_record_based_on: input_based_on.value
                },
                callback: function(r) {
                    if (r.message) {
                        grid_data = r.message;
                        render_grid(grid_data);
                        toastr.success("System attendance fetched successfully.");
                    }
                },
                always: function() {
                    btn_fetch.innerText = "Fetch System Attendance";
                    is_fetching = false;
                }
            });
        });
    }

    function collect_payload() {
        // Build payload matching grid_data structure but with updated inputs
        let updated_data = JSON.parse(JSON.stringify(grid_data)); // deep copy

        document.querySelectorAll(".cell-input").forEach(input => {
            let emp_id = input.getAttribute("data-emp");
            let day_num = input.getAttribute("data-day");
            let val = input.value;

            // Find employee
            let emp = updated_data.find(e => e.employee === emp_id);
            if (emp && emp.days && emp.days[day_num]) {
                if (ctx.based_on === "Attendance Status") {
                    emp.days[day_num].value = val;
                } else {
                    emp.days[day_num].value = val;
                }
            }
        });

        return updated_data;
    }

    // Event: Save
    if (btn_save) {
        btn_save.addEventListener("click", function() {
            if (!validate_date_buffer(input_to.value || ctx.to_date)) return;
            
            let payload = collect_payload();
            if (payload.length === 0) return toastr.warning("No data to save.");
            
            let btn_orig = btn_save.innerText;
            btn_save.innerText = "Saving...";
            btn_save.disabled = true;

            frappe.call({
                method: "one_fm.one_fm.doctype.subcontract_staff_attendance.subcontract_staff_attendance.save_attendance_records",
                args: {
                    subcontractor_name: ctx.supplier,
                    from_date: input_from.value || ctx.from_date,
                    to_date: input_to.value || ctx.to_date,
                    based_on: input_based_on.value || ctx.based_on,
                    rows_json: JSON.stringify(payload),
                    submit: 0
                },
                callback: function(r) {
                    btn_save.innerText = btn_orig;
                    btn_save.disabled = false;
                    if (!r.exc) {
                        toastr.success("Saved successfully.");
                        // Redirect to list page
                        setTimeout(() => location.href = '/subcontractor-attendance', 1000);
                    }
                }
            });
        });
    }

    // Event: Submit
    if (btn_submit) {
        btn_submit.addEventListener("click", function() {
            if (!validate_date_buffer(input_to.value || ctx.to_date)) return;
            
            let payload = collect_payload();
            if (payload.length === 0) return toastr.warning("No data to submit.");
            
            frappe.confirm("Are you sure you want to submit? Once submitted, you will not be able to edit these records anymore.", function() {
                let btn_orig = btn_submit.innerText;
                btn_submit.innerText = "Submitting...";
                btn_submit.disabled = true;
                if (btn_save) btn_save.disabled = true;

                frappe.call({
                    method: "one_fm.one_fm.doctype.subcontract_staff_attendance.subcontract_staff_attendance.save_attendance_records",
                    args: {
                        subcontractor_name: ctx.supplier,
                        from_date: input_from.value || ctx.from_date,
                        to_date: input_to.value || ctx.to_date,
                        based_on: input_based_on.value || ctx.based_on,
                        rows_json: JSON.stringify(payload),
                        submit: 1
                    },
                    callback: function(r) {
                        btn_submit.innerText = btn_orig;
                        btn_submit.disabled = false;
                        if (!r.exc) {
                            frappe.msgprint({title: "Success", message: "Records submitted successfully.", indicator: "green"});
                            setTimeout(() => location.href = "/subcontractor-attendance", 2000);
                        } else {
                            if (btn_save) btn_save.disabled = false;
                        }
                    }
                });
            });
        });
    }

    // Story 1: Row Expansion
    window.open_row_detail = function(emp_id) {
        let payload = collect_payload();
        let emp = payload.find(e => e.employee === emp_id);
        if (!emp) return;

        document.getElementById("detail-employee-name").innerText = emp.employee_name + " (" + emp.employee_id + ")";
        let based_on = input_based_on.value || ctx.based_on;

        let tbody = "";
        let remarks_set = new Set();
        let from_date = moment(input_from.value || ctx.from_date);
        let to_date = moment(input_to.value || ctx.to_date);
        let days_in_range = to_date.diff(from_date, 'days') + 1;
        
        let w_days = 0;
        let o_days = 0;
        let w_hours = 0;

        for (let i = 0; i < days_in_range; i++) {
            let current_date = moment(from_date).add(i, 'days');
            let day_num = current_date.date();
            let d_data = (emp.days && emp.days[day_num]) || null;
            
            let val = "-";
            let site = "-";
            if (d_data) {
                if (d_data.remarks) remarks_set.add(`[${d_data.site}]: ${d_data.remarks}`);
                site = d_data.site || "-";
                let tally_val = based_on === "Attendance Status" ? d_data.value : (d_data.status_val || "");
                
                if (based_on === "Attendance Status") {
                    val = d_data.value || "-";
                    if (["Present", "Half Day", "Work From Home"].includes(val)) w_days++;
                } else {
                    val = d_data.value ? parseFloat(d_data.value) : "-";
                    let hrs = parseFloat(d_data.value);
                    if (hrs > 0) {
                        w_days++;
                        w_hours += hrs;
                    }
                }
                
                if (["Day Off", "Client Day Off"].includes(tally_val)) o_days++;
            }

            tbody += `<tr>
                <td>Day ${i + 1}</td>
                <td>${current_date.format("D MMM YYYY")}</td>
                <td class="font-weight-bold">${val}</td>
                <td class="text-muted">${site}</td>
            </tr>`;
        }

        let total_w_display = based_on === "Shift Hours" ? `${w_days} Shifts (${w_hours.toFixed(1)} hrs)` : `${w_days} Working Days`;
        document.getElementById("detail-working-days").innerText = total_w_display;
        document.getElementById("detail-off-days").innerText = `${o_days} Days Off`;

        document.getElementById("detail-days-table").querySelector("tbody").innerHTML = tbody;
        
        let remarks_html = Array.from(remarks_set).join("<br/>") || "No remarks found.";
        document.getElementById("detail-remarks").innerHTML = remarks_html;

        $('#rowDetailModal').modal('show');
    };

    // Story 3: Preview Attendance
    let btn_preview = document.getElementById("btn-preview");
    if (btn_preview) {
        btn_preview.addEventListener("click", function() {
            let based_on = input_based_on.value || ctx.based_on;
            
            let from_date = moment(input_from.value || ctx.from_date);
            let to_date = moment(input_to.value || ctx.to_date);
            let days_in_range = to_date.diff(from_date, 'days') + 1;

            let top_headers = `<th rowspan="2" style="vertical-align: middle;">Employee ID</th><th rowspan="2" style="vertical-align: middle;">Employee Name</th>`;
            let bottom_headers = ``;
            for (let i = 0; i < days_in_range; i++) {
                let current_date = moment(from_date).add(i, 'days');
                let is_friday = current_date.day() === 5;
                top_headers += `<th class="${is_friday ? 'bg-light' : ''}" style="min-width: 40px; text-align: center;">${current_date.format("ddd")}</th>`;
                bottom_headers += `<th class="${is_friday ? 'bg-light' : ''}" style="min-width: 40px; text-align: center;">${current_date.format("D/M")}</th>`;
            }
            top_headers += `<th rowspan="2" style="text-align: center; vertical-align: middle;">Working Days</th><th rowspan="2" style="text-align: center; vertical-align: middle;">Days Off</th>`;
            
            document.getElementById("preview-header-days").innerHTML = top_headers;
            document.getElementById("preview-header-dates").innerHTML = bottom_headers;

            let tbody = "";

            grid_data.forEach(emp => {
                let w_days = 0;
                let o_days = 0;
                let w_hours = 0;
                
                let cells_html = `<td>${emp.employee_id}</td><td>${emp.employee_name}</td>`;
                
                for (let i = 0; i < days_in_range; i++) {
                    let current_date = moment(from_date).add(i, 'days');
                    let day_num = current_date.date();
                    let d_data = (emp.days && emp.days[day_num]) || null;
                    
                    let val_display = "";
                    if (d_data) {
                        let tally_val = based_on === "Attendance Status" ? d_data.value : d_data.status_val;
                        
                        if (based_on === "Shift Hours") {
                            let hrs = parseFloat(d_data.value);
                            if (hrs > 0) {
                                w_days++;
                                w_hours += hrs;
                            }
                            val_display = hrs > 0 ? hrs : "";
                        } else if (based_on === "Attendance Status") {
                            if (["Present", "Half Day", "Work From Home"].includes(tally_val)) {
                                w_days++;
                            }
                            let val = d_data.value || "";
                            val_display = status_maps[val] || val;
                        }
                        
                        if (["Day Off", "Client Day Off"].includes(tally_val)) {
                            o_days++;
                        }
                    }
                    
                    cells_html += `<td style="text-align: center; vertical-align: middle;">${val_display}</td>`;
                }

                let total_display = based_on === "Shift Hours" ? `${w_days} Shifts (${w_hours.toFixed(1)} hrs)` : `${w_days}`;

                tbody += `<tr>
                    ${cells_html}
                    <td class="font-weight-bold text-center" style="vertical-align: middle;">${total_display}</td>
                    <td class="font-weight-bold text-center" style="vertical-align: middle;">${o_days}</td>
                </tr>`;
            });

            document.getElementById("preview-table-body").innerHTML = tbody;
            $('#previewModal').modal('show');
        });
    }

});
