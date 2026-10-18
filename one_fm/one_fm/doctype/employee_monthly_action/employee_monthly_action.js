// Copyright (c) 2025, ONE FM and contributors
// For license information, please see license.txt
frappe.ui.form.on('Employee Monthly Action', {
    onload: function (frm) {
        if (frm.is_new()) {
            set_employee_from_the_session_user(frm);
            const today = new Date();
            const monthOptions = frm.fields_dict.month.df.options.split('\n');

            frm.set_value('month', monthOptions[today.getMonth()+1]);
            frm.set_value('year', today.getFullYear().toString());
        }
    },
    employee: function (frm) {
      frm.events.set_goal_details(frm);
    },
    month: function (frm) {
      frm.events.set_goal_details(frm);
    },
    year: function (frm) {
      frm.events.set_goal_details(frm);
    },
    set_goal_details: function(frm) {
      if (!frm.doc.employee || !frm.doc.year || !frm.doc.month){
        frm.clear_table('goal_update');
        frm.refresh_field('goal_update');
        return;
      }

      frappe.call({
        method: 'one_fm.overrides.goal.get_goals_for_employee',
        args: {
          employee: frm.doc.employee,
          year: frm.doc.year,
          month: frm.doc.month
        },
        callback: function (r) {
          if (r.message) {
            frm.clear_table('goal_update');

            r.message.forEach(goal => {
              const row = frm.add_child('goal_update');
              row.goal = goal.name;
              row.previous_progress = goal.progress;
            });

            frm.refresh_field('goal_update');
          }
        }
      });
    }
});

function set_employee_from_the_session_user(frm) {
	if(frappe.session.user != 'Administrator' && frm.is_new() && !frm.doc.amended_from){
		frappe.db.get_value('Employee', {'user_id': frappe.session.user} , 'name', function(r) {
			if(r && r.name){
				frm.set_value('employee', r.name);
			}
			else{
				frappe.show_alert({
					message: __('Not find employee record for the user <b>{0}</b>', [frappe.session.user]),
					indicator: 'yellow'
				});
			}
		});
	}
};
