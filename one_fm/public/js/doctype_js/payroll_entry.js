frappe.ui.form.on('Payroll Entry', {
	onload: function (frm) {
		frm.events.project_filters(frm);
	},
	project_filters: function (frm) {
		if(frm.doc.start_date && frm.doc.start_date){
			let {start_date, end_date} = frm.doc;
			frm.set_query("custom_project_filter", function () {
				return {
					filters: {
						company: frm.doc.company,
						project_type: "External",
						custom_payroll_start_date: moment(start_date).date(),
						custom_payroll_end_date: moment(end_date).date()
					},
				};
			});	
		}
		else {
			frm.set_query("custom_project_filter", function () {
				return {
					filters: {
						company: frm.doc.company,
						project_type: "External",
					},
				};
			});
		}
	},
	start_date: function (frm) {
		frm.events.project_filters(frm);
	},
	end_date: function (frm) {
		frm.events.project_filters(frm);
	},
	custom_project_configuration: function (frm) {
		frm.events.clear_employee_table(frm);
	},
	custom_project_filter: function (frm) {
		frm.events.clear_employee_table(frm);
	},
})