// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee ID', {
	validate: function(frm) {
		create_qr_code(frm);
	}
});

var create_qr_code = function(frm) {
	if(!frm.doc.qr_code_image_link){
		var chart = "http://chart.googleapis.com/chart?cht=qr&chs=200x200&chl=";
		var fields = ['Employee Name', 'Employee Name in Arabic', 'Designation', 'Designation in Arabic', 'Date of Birth',
			'Date of Joining', 'CIVIL ID']
		var qr_details = ""
		fields.forEach((field, i) => {
			if(field == 'Date of Joining'){
				qr_details += field+": "+frappe.datetime.global_date_format(frm.doc.date_of_joining)+"\n";
			}
			else if(field == 'Date of Birth'){
				qr_details += field+": "+frappe.datetime.global_date_format(frm.doc.date_of_birth)+"\n";
			}
			else if(field == 'Employee Name in Arabic'){
				qr_details += field+": "+frm.doc.employee_name_in_arabic+"\n";
			}
			else{
				qr_details += field+": "+frm.doc[field.toLowerCase().replace(' ', '_')]+"\n";
			}
		});
		var chart_url = chart+encodeURI(qr_details);
		frm.set_value("qr_code_image_link", chart_url);
	}
};
