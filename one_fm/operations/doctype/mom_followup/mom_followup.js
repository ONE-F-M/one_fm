// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('MOM Followup', {
	
		after_workflow_action: function(frm) {
		if(frm.doc.workflow_state=='Issue Penalty'){
			console.log('OK THIS WORKS!')
			let penalty = new frappe.ui.Dialog({
				'fields':[
					{'label': 'Penalty Type',
					 'fieldname':'penalty_type',
					 'fieldtype':'Link',
					 'options': 'Penalty Type',
					 'reqd': 1,

					//  'fieldtype':'Table',
					//  'fields':[{
					// 	'label': 'Penalty Type',
					// 	'fieldname':'penalty_type',
					// 	'fieldtype':'Link',
					// 	'options': 'Penalty Type',
					// 	'in_list_view':1,
						// 'onchange':function(){
						// 	let penalty_type = penalty.fields_dict.penalty_details.get_value("penalty_type")


						// }

					 },
					//  {
					// 	'label': 'Penalty Type Arabic',
					// 	'fieldname':'penalty_type_arabic',
					// 	'fieldtype':'Data',
					// 	'fetch_from': 'penalty.get_value("penalty_type")',
					// 	'in_list_view':1,

					//  },
					

					 
			
					{
						'label': 'Penalty Notes',
						'fieldname':'penalty_notes',
						'fieldtype':'Small Text',

					 }
				],
				primary_action: function(){
					// frappe.model.set_value(frm.doc.doctype,frm.doc.name,"penalty_type",frm.doc.penalty_type);
					
					penalty.hide();
					var args = penalty.get_values();
					frm.set_value("penalty_note",args.penalty_notes);
					frm.set_value("penalty_type",args.penalty_type);
					console.log(args);

					// args.penalty_details.forEach((penalty) => {
					// 	let child_row = frappe.model.add_child(frm.doc, "penalty_table");
					// 	child_row.penalty_type = penalty.penalty_type;
					
					// });
					frm.refresh_fields("penalty_table");
					frm.save("Update");

				}
			});
			penalty.show();
			
			

		// }
		// 
		console.log('OK THIS WORKS!')
								}
	}

});
