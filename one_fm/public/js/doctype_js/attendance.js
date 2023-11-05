frappe.ui.form.on('Attendance', {
	refresh: function(frm){
        frm.trigger('show_working_hours');
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
    }
});
