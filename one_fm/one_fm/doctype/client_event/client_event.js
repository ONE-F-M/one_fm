// Copyright (c) 2025, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Client Event", {
    setup(frm) {
        // Filter original_client_event to only show Approved events that haven't been extended
        frm.set_query("original_client_event", function() {
            return {
                query: "one_fm.one_fm.doctype.client_event.client_event.get_extensible_client_events"
            };
        });
    },
    refresh(frm) {
        frm.events.add_event_staff(frm);
        frm.events.add_extension_button(frm);
    },
    add_extension_button(frm) {
        if (frm.doc.workflow_state !== "Approved" || frm.doc.docstatus !== 1) {
            return;
        }
        // Check if extension already exists
        frappe.xcall("frappe.client.get_count", {
            doctype: "Client Event",
            filters: {
                "original_client_event": frm.doc.name,
                "docstatus": ["<", 2]
            }
        }).then((count) => {
            if (!count) {
                frm.add_custom_button(__("Client Event Extension"), function() {
                    frappe.call({
                        method: "one_fm.one_fm.doctype.client_event.client_event.create_client_event_extension",
                        args: { source_name: frm.doc.name },
                        callback: function(r) {
                            if (r.message) {
                                let new_doc = r.message;
                                frappe.model.sync(new_doc);
                                frappe.set_route("Form", "Client Event", new_doc.name);
                            }
                        }
                    });
                });
            }
        });
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


