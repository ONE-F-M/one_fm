// Copyright (c) 2025, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Client Event", {
    refresh(frm) {
        frm.events.add_event_staff(frm);
    },
    add_event_staff(frm) {
        if (["Approved", "Pending Operations Manager"].includes(frm.doc.workflow_state)) {
            frm.add_custom_button(__("Add Staff to Event"), function() {
                let d = new frappe.ui.Dialog({
                    title: __("Add Staff to Event"),
                    fields: get_add_staff_event_dialog_fields(frm),
                    primary_action_label: __("Submit"),
                    primary_action: (values) => {
                        frm.events.submit_event_staff(frm, values);
                        d.hide();
                    },
                });
                d.show();
            });
        }
    },
    submit_event_staff(frm, values) {
        frm.call({
            method: "add_event_staff",
            doc: frm.doc,
            args: {
                staff: JSON.stringify(values.staff)
            },
            callback: function(r) {
                if (r.message) {
                    frappe.show_alert(__("Event Staff added successfully."));
                }
            }
        });
    }
});

function get_add_staff_event_dialog_fields(frm) {
    return [
    {
            label: __("Staff"),
            fieldname: "staff",
            fieldtype: "Table",
            fields: [
                {
                    label: __("Employee"),
                    fieldname: "employee",
                    fieldtype: "Link",
                    options: "Employee",
                    in_list_view: 1,
                    reqd: 1,
                    get_query: () => {
                        let designations = (frm.doc.staffing_requirements || []).map(d => d.designation);
                        return {
                            filters: {
                                designation: ["in", designations]
                            }
                        };
                    },
                    onchange: function() {
                        let employee = this.get_value();
                        let row = this.grid_row;
                        if (employee) {
                            row.doc.roster_type = 'Basic';
                            frappe.db.get_value('Employee', employee, 'designation', (r) => {
                                row.doc.designation = r.designation;
                                row.refresh();
                            });
                        }
                    }
                },
                {
                    label: __("Designation"),
                    fieldname: "designation",
                    fieldtype: "Link",
                    options: "Designation",
                    in_list_view: 1,
                    reqd: 1,
                },
                {
                    label: __("Roster Type"),
                    fieldname: "roster_type",
                    fieldtype: "Select",
                    options: "Basic\nOver-Time",
                    in_list_view: 1,
                    reqd: 1,
                },
                {
                    label: __("Day Off OT"),
                    fieldname: "day_off_ot",
                    fieldtype: "Check",
                    depends_on: "eval:doc.roster_type=='Basic'",
                },
                {
                    label: __("Operations Shift"),
                    fieldname: "operations_shift",
                    fieldtype: "Link",
                    options: "Operations Shift",
                },
            ],
        },
    ]
}


