// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Medical Insurance', {
	civil_id: function(frm) {
		if(frm.doc.civil_id){
			frappe.call({
				method: 'one_fm.grd.doctype.medical_insurance.medical_insurance.get_employee_data_from_civil_id',
				args:{'civil_id': frm.doc.civil_id},
				callback: function(r) {
					if(r && r.message){
						var data = r.message;
						frm.set_value('employee_name', data.employee_name);
						frm.set_value('gender', data.gender);
						frm.set_value('nationality', data.one_fm_nationality);
						frm.set_value('passport_expiry_date', data.valid_upto);
					}
					frm.refresh_fields();
				},
				freaze: true,
				freaze_message: __("Fetching Data with CIVIL ID")
			});
		}
	}
});

frappe.ui.form.on('Medical Insurance Item', {
	civil_id: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		if(child.civil_id){
			frappe.call({
				method: 'one_fm.grd.doctype.medical_insurance.medical_insurance.get_employee_data_from_civil_id',
				args:{'civil_id': child.civil_id},
				callback: function(r) {
					if(r && r.message){
						var data = r.message;
						frappe.model.set_value(cdt, cdn, 'employee_name', data.employee_name);
						frappe.model.set_value(cdt, cdn, 'gender', data.gender);
						frappe.model.set_value(cdt, cdn, 'nationality', data.one_fm_nationality);
						frappe.model.set_value(cdt, cdn, 'passport_expiry_date', data.valid_upto);
					}
					frm.refresh_fields();
				},
				freaze: true,
				freaze_message: __("Fetching Data with CIVIL ID")
			});
		}
	}
});
