frappe.ui.form.on('Payroll Entry', {
    refresh: function(frm) {
		if (frm.doc.salary_slips_created == 1){
			frm.add_custom_button(__("Download Payroll Bank Export File"), function() {
				let payroll_entry = frm.doc.name
				// Fetch URi for the export file
				frappe.xcall("one_fm.api.doc_methods.payroll_entry.get_excel_payroll_export_file", {payroll_entry})
					.then(res => {
						let {filename, uri} = res
						if(uri && filename) {
							// Downaload file
							download(uri, filename)
						}else{
							frappe.throw(_("No Export file found."))
						}
					})
			}).addClass("btn-primary");
		}
		frm.set_indicator_formatter('employee',
				function(doc) {
					return (doc.justification_needed_on_deduction == 1) ? "orange" : "green";
				}
		);
    }
});

/**
 * This function downloads the file from a given URi provided a filename.
 * @param {string} uri - uri of the file
 * @param {string} name - name of the file
 */
function download(uri, name) {
    var link = document.createElement("a");
    link.download = name;
    link.href = uri;
    link.click();
}
