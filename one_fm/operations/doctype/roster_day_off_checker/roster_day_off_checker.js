// Copyright (c) 2022, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on('Roster Day Off Checker', {
    refresh: function(frm) {
        add_make_cdo_button(frm);
    }
});

function add_make_cdo_button(frm) {
    if (!frm.doc.__islocal && 
        frm.doc.status !== 'Cancelled' &&
        (frappe.user.has_role('Payroll Operator') || 
         frappe.user.has_role('Attendance Manager') || 
         frappe.session.user === "Administrator")) {
        
        frm.add_custom_button(__('Make CDO'), function() {
            show_make_cdo_dialog(frm);
        });
    }
}

function show_make_cdo_dialog(frm) {
    let dialog = new frappe.ui.Dialog({
        title: __('Make Client Day Off'),
        fields: [
            {
                fieldname: 'employee_name',
                label: __('Employee Name'),
                fieldtype: 'Data',
                read_only: 1,
                default: frm.doc.employee_name || frm.doc.employee
            },
            {
                fieldname: 'attendance_date',
                label: __('Attendance Date'),
                fieldtype: 'Date',
                reqd: 1,
                description: __('Select a past date only')
            },
            {
                fieldname: 'attendance_status',
                label: __('Attendance Status'),
                fieldtype: 'Data',
                read_only: 1,
                default: 'Client Day Off'
            }
        ],
        primary_action_label: __('Update Attendance'),
        primary_action: function(values) {
            let selected_date = frappe.datetime.str_to_obj(values.attendance_date);
            let today = frappe.datetime.now_date(true);
            
            if (selected_date >= today) {
                frappe.msgprint({
                    title: __('Invalid Date'),
                    message: __('Please select a date earlier than today. Current and future dates are not allowed.'),
                    indicator: 'red'
                });
                return;
            }
            
            frappe.call({
                method: 'one_fm.operations.doctype.roster_day_off_checker.roster_day_off_checker.update_attendance_to_cdo',
                args: {
                    employee: frm.doc.employee,
                    attendance_date: values.attendance_date
                },
                freeze: true,
                freeze_message: __('Updating Attendance...'),
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frappe.msgprint({
                            title: __('Success'),
                            message: r.message.message,
                            indicator: 'green'
                        });
                        dialog.hide();
                    } else if (r.message && r.message.error) {
                        frappe.msgprint({
                            title: __('Error'),
                            message: r.message.message,
                            indicator: 'red'
                        });
                    }
                }
            });
        }
    });
    
    dialog.show();
}