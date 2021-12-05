frappe.ui.form.on('Payroll Entry', {
    refresh: function(frm) {
		if (frm.doc.salary_slips_created == 1){
			frm.add_custom_button(__("Download Payroll Bank Export File"), function() {
				let payroll_entry = frm.doc.name
				// Fetch URL for the export file
				frappe.xcall("one_fm.api.doc_methods.payroll_entry.download_excel_payroll_export_file", {payroll_entry})
					.then(res => {
						let {app_url, path, filename} = res;
						if (app_url && path && filename){
							let url = app_url + path + filename
							window.open(url, "Download");
						}else{
							frappe.throw(_("Invalid URL"))
						}
					}).catch(e =>{
						console.log(e);
					});
			}).addClass("btn-primary");
		}
		frm.set_indicator_formatter('employee',
				function(doc) {
					return (doc.justification_needed_on_deduction == 1) ? "orange" : "green";
				}
		);
    }
});