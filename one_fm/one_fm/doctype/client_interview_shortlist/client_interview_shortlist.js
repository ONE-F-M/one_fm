// Copyright (c) 2025, ONE FM and contributors
// For license information, please see license.txt

let skip_attendance_confirmation = false;

frappe.ui.form.on("Client Interview Shortlist", {
	refresh(frm) {
        if (frm.doc.docstatus === 1) {
            // Remove add row button from specific child table
            frm.fields_dict['client_interview_employee'].grid.cannot_add_rows = true;
            frm.fields_dict['client_interview_employee'].grid.refresh();
        }
        skip_attendance_confirmation = false;
	},
    onload(frm) {
        skip_attendance_confirmation = false;
    },
    set_skip_confirmation(values) {
        // Check if user wants to skip future confirmations
        if (values.dont_ask_again) {
            skip_attendance_confirmation = true;
            frappe.show_alert({
                message: __('Confirmation will be skipped for remaining employees'),
                indicator: 'blue'
            }, 3);
        }
    },

    before_workflow_action(frm) {
        // Story 2: Show informational warning for unchecked attendance/selection
        // when the Operations Supervisor clicks Submit
        if (frm.selected_workflow_action === "Submit") {
            let unchecked_rows = [];
            (frm.doc.client_interview_employee || []).forEach(function(row) {
                if (!row.attended || !row.selected) {
                    unchecked_rows.push(row);
                }
            });

            if (unchecked_rows.length > 0) {
                let row_details = unchecked_rows.map(function(row) {
                    return __("Row {0}: {1}", [row.idx, row.employee_name || row.employee]);
                }).join("<br>");

                frappe.msgprint({
                    title: __("Attendance / Selection Status"),
                    indicator: "red",
                    message: __(
                        "The following Employees Attendance or Selection status have not been checked for client interview:<br><br>"
                        + "{0}"
                        + "<br><br>But, if the employee has not been attended or has not been selected, then you can keep it unchecked.",
                        [row_details]
                    )
                });
            }
        }
    }
});

frappe.ui.form.on("Client Interview Employee", {
    attended(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);

        if (row.attended) {
            // If user previously chose to skip, don't show confirmation
            if (skip_attendance_confirmation) {
                return;
            }

            // Show custom dialog with "Don't ask again" option
            let d = new frappe.ui.Dialog({
                title: __('Confirm Attendance'),
                fields: [
                    {
                        fieldtype: 'HTML',
                        options: '<p>Are you sure you want to mark this employee as attended?</p>'
                    },
                    {
                        fieldname: 'dont_ask_again',
                        fieldtype: 'Check',
                        label: __("Don't ask again for remaining employees")
                    }
                ],
                primary_action_label: __('Yes'),
                primary_action: function(values) {
                    frm.events.set_skip_confirmation(values);
                    d.hide();
                },
                secondary_action_label: __('No'),
                secondary_action: function() {
                    let values = d.get_values();
                    frm.events.set_skip_confirmation(values);
                    // Revert the checkbox if user selects No
                    frappe.model.set_value(cdt, cdn, "attended", 0);
                    d.hide();
                }
            });

            d.$wrapper.on('hide.bs.modal', function() {
                if(!d.primary_action_fulfilled) {
                    // Revert the checkbox if dialog was closed without confirmation
                    frappe.model.set_value(cdt, cdn, "attended", 0);
                    frm.refresh_field("client_interview_employee");
                }
            });

            d.show();
        }
        else {
            // If unchecked, ensure selected is also unchecked
            frappe.model.set_value(cdt, cdn, "selected", 0);
            frm.refresh_field("client_interview_employee");
        }
    }
});