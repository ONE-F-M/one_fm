frappe.ui.form.on('Payroll Entry', {
	// onload: function(frm){
	// 	check_salary_slip_counts(frm)
	// },
    refresh: function(frm) {
		if(!frm.is_new() && frm.doc.salary_slips_created == 1){
			check_salary_slip_counts(frm)
		}
		if (frm.doc.status == "Pending Salary Slip"){
			frm.add_custom_button(__("Create Pending Salary Slip"), function() {
				frm.trigger("create_pending_salary_slip");
			}).addClass("btn-warning");
		}
		if (frm.doc.salary_slips_created == 1 && frm.doc.bank_account){
			frm.add_custom_button(__("Download Payroll Bank Export"), function() {
				let payroll_entry = frm.doc.name
				window.open("/files/payroll-entry/" + payroll_entry + ".xlsx", "Download");
			}).addClass("btn-primary");
			frm.add_custom_button(__("Download Payroll Cash Export"), function() {
				let payroll_entry = "Cash-" + frm.doc.name
				window.open("/files/payroll-entry/" + payroll_entry + ".xlsx", "Download");
			}).addClass("btn-primary");
		}
		frm.set_indicator_formatter('employee',
				function(doc) {
					return (doc.justification_needed_on_deduction == 1) ? "orange" : "green";
				}
		);
    },
	create_pending_salary_slip: function(frm){
		create_sal_slip(frm)
	}
});
var check_salary_slip_counts = function(frm){
	frappe.call({
		method: 'one_fm.api.doc_methods.payroll_entry.check_salary_slip_count',
		args: {
			doc: frm.doc.name
		},
		callback: function (r) {
			if(r.message){
				console.log(r.message)
			}
		},
	});
}

var create_sal_slip = function(frm){
	frappe.call({
		method: 'one_fm.api.doc_methods.payroll_entry.create_pending_sal_slip',
		args: {
			doc: frm.doc.name
		},
		callback: function (r) {
			if(r.message){
				console.log(r.message)
				frm.refresh();
			}
		},
	});
}