frappe.ui.form.on('Gratuity', {
	refresh: function(frm) {
	},
	employee: frm=>{
		if(frm.doc.employee){
            frappe.db.get_value("Employee", frm.doc.employee, 'date_of_joining').then(res=>{
                console.log(frappe.datetime.get_diff(frappe.datetime.get_today(), res.message.date_of_joining)/365)
                frm.set_value('current_work_experience', frappe.datetime.get_diff(frappe.datetime.get_today(), res.message.date_of_joining)/365)
            })
        }
	}
});