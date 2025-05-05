// Copyright (c) 2025, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on("Department Weekly Review", {
	onload(frm) {
        if (frm.is_new()) {
            set_current_week_and_year(frm)
            fetch_user_department(frm).then((r) => {
                const { department } = r.message
                
                if (department) {
                    frm.set_value('department', department)

                    // Load department relevant data
                    load_department_employees(frm, department)
                    load_department_blockers(frm, department)
                }
            });
        }
    }
});

const set_current_week_and_year = (frm) => {
    frappe.call({
        method: 'one_fm.utils.get_current_year_and_week',
        callback: function(r) {
            if (r.message) {
                frm.set_value(r.message);
            }
        }
    });
};

const fetch_user_department = () => {
    return frappe.db.get_value('Employee', { user_id: frappe.session.user }, 'department')
};

const load_department_employees = (frm, department) => {
    frappe.call({
        method: "one_fm.one_fm.doctype.department_weekly_review.department_weekly_review.get_employees_by_department",
        args: { department },
        callback: function (r) {
            if (r.message && Array.isArray(r.message)) {
                frm.clear_table("attendees");

                r.message.forEach(emp => {
                    const row = frm.add_child("attendees");
                    row.employee = emp.name;
                    row.employee_name = emp.employee_name;
                });

                frm.refresh_field("attendees");
            }
        }
    });
};

const load_department_blockers = (frm, department) => {
    frappe.call({
        method: "one_fm.one_fm.doctype.department_weekly_review.department_weekly_review.get_blockers_by_department",
        args: { department },
        callback: function (r) {
            if (r.message && Array.isArray(r.message)) {
                frm.clear_table("blockers");

                r.message.forEach(item => {
                    const row = frm.add_child("blockers");
                    row.blocker = item.blocker_details;
                    row.employee_name = item.employee_name;
                    row.since = item.date;
                    row.assigned = item.assigned_to;
                });

                frm.refresh_field("blockers");
            }
        }
    });
};
