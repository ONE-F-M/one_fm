// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt
frappe.ui.form.on('Preparation',{
	refresh: function(frm)
	{

	}

	
});

frappe.ui.form.on('Preparation Record',{
renewal_or_extend: function(frm, cdt, cdn){
	var row = locals[cdt][cdn];
	if(row.renewal_or_extend == "Renewal"){
		frappe.model.set_value(cdt, cdn, "ref_doctype", 'Work Permit');
		frappe.model.set_value(cdt, cdn, "ref_name", work_permit.name);

	}
	else{
		frappe.model.set_value(cdt, cdn, "ref_doctype", 'MOI Residency Jawazat');
		frappe.model.set_value(cdt, cdn, "ref_name", moi_residency_jawazat.name);
	}
}
});
