// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt
frappe.ui.form.on('Preparation',{
	// refresh: function(frm){
		
		

	// },
	
});

frappe.ui.form.on('Preparation Record',{
//set total amunt per employee on the selection of the process
renewal_or_extend: function(frm, cdt, cdn){
	if(frm.doc.renewal_or_extend != ""){
		var row = locals[cdt][cdn];
		if(row.work_permit_amount && row.medical_insurance_amount && row.residency_stamp_amount && row.civil_id_amount){
			let total = row.work_permit_amount+row.medical_insurance_amount+row.residency_stamp_amount+row.civil_id_amount;
			row.total_amount = total;
			frm.save();
		}
	}
	// if(row.renewal_or_extend == "Renewal"){
	// 	frappe.model.set_value(cdt, cdn, "ref_doctype", 'Work Permit');
	// 	frappe.model.set_value(cdt, cdn, "ref_name", work_permit.name);
	// 	console.log(frm.set_renewal_for_all)

	// }
	// else{
	// 	frappe.model.set_value(cdt, cdn, "ref_doctype", 'MOI Residency Jawazat');
	// 	frappe.model.set_value(cdt, cdn, "ref_name", moi_residency_jawazat.name);
	// }
},


});
//Set renewal for all employee to facilitate process
frappe.ui.form.on("Preparation", {
    "set_renewal_for_all": function(frm) {
		if(frm.doc.preparation_record && frm.doc.set_renewal_for_all == 1){
			$.each(frm.doc.preparation_record || [], function(i, v) {
				frappe.model.set_value(v.doctype, v.name, "renewal_or_extend", "Renewal")
			})
		}
		else if (frm.doc.preparation_record && frm.doc.set_renewal_for_all == 0){
			$.each(frm.doc.preparation_record || [], function(i, v) {
				frappe.model.set_value(v.doctype, v.name, "renewal_or_extend", " ")
			})
			
		}
	},//set total payment for the whole list on HR approval
	"hr_approval": function(frm){
		if(frm.doc.hr_approval == "Yes"){
		let total = 0;
		$.each(frm.doc.preparation_record || [], function(i, v) {
				total+= v.total_amount;
			})
				frm.set_value('total_payment',total);
		}
	}
  
});
