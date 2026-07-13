frappe.ui.form.on('Attendance', {
	refresh: function(frm){
        frm.trigger('show_working_hours');
        frm.trigger('setup_attendance_correction');
	},
    status: function(frm){
        frm.trigger('show_working_hours');
    },
    show_working_hours: function(frm){
        if (['Present', 'Work From Home'].includes(frm.doc.status)){
            frm.toggle_display('working_hours', 1);
            frm.toggle_enable('working_hours', 1);
        } else {
            frm.toggle_display('working_hours', 0);
            frm.toggle_enable('working_hours', 1);
        }
    },
    setup_attendance_correction: function(frm){
        // Only Payroll Operators may correct a submitted, Basic-roster Attendance,
        // only until the end of the month following the attendance month, and only
        // once (a stored correction reason hides the button permanently).
        if (
            frm.doc.docstatus === 1 &&
            frm.doc.roster_type === 'Basic' &&
            !frm.doc.custom_correction_reason &&
            frappe.user_roles.includes('Payroll Operator') &&
            is_within_correction_window(frm.doc.attendance_date)
        ){
            frm.add_custom_button(__('Attendance Correction'), function(){
                show_attendance_correction_dialog(frm);
            });
        }
    }
});

function is_within_correction_window(attendance_date){
    // Allowed through the last day of the month following the attendance month (inclusive).
    if (!attendance_date){
        return false;
    }
    let att = frappe.datetime.str_to_obj(attendance_date);
    // new Date(year, monthIndex, 0) => last day of (monthIndex - 1);
    // last day of (attendance month + 1) => monthIndex = att_month + 2.
    let deadline = new Date(att.getFullYear(), att.getMonth() + 2, 0);
    deadline.setHours(23, 59, 59, 999);
    let today = frappe.datetime.str_to_obj(frappe.datetime.get_today());
    return today <= deadline;
}

function show_attendance_correction_dialog(frm){
    let d = new frappe.ui.Dialog({
        title: __('Attendance Correction'),
        fields: [
            {
                fieldname: 'day_off_ot',
                fieldtype: 'Check',
                label: __('Day Off OT'),
                default: frm.doc.day_off_ot
            },
            {
                fieldname: 'reason',
                fieldtype: 'Small Text',
                label: __('Reason for Change'),
                reqd: 1,
                default: __('Correcting Roster Mistake')
            }
        ],
        primary_action_label: __('Submit'),
        primary_action: function(values){
            frappe.call({
                method: 'one_fm.overrides.attendance.apply_attendance_correction',
                args: {
                    attendance: frm.doc.name,
                    day_off_ot: values.day_off_ot ? 1 : 0,
                    reason: values.reason
                },
                freeze: true,
                freeze_message: __('Applying correction...'),
                callback: function(r){
                    if (r.message && r.message.success){
                        d.hide();
                        frappe.show_alert({
                            message: __('Attendance corrected successfully.'),
                            indicator: 'green'
                        });
                        frm.reload_doc();
                    }
                }
            });
        }
    });
    d.show();
}
