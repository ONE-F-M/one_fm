// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt
// frappe.ui.form.on('Target DocType', {
//     link_to_source: function (frm) {
//         if (frm.doc.link_to_source) {
//             frm.clear_table('target_table');
//             frappe.model.with_doc('Source DocType', frm.doc.link_to_source, function () {
//                 let source_doc = frappe.model.get_doc('Source DocType', frm.doc.link_to_source);
//                 $.each(source_doc.source_table, function (index, source_row) {
//                     frm.add_child('target_table').column_name = source_row.column_name; // this table has only one column. You might want to fill more columns.
//                     frm.refresh_field('target_table');
//                 });
//             });
//         }
//     },
// });
frappe.ui.form.on('Pre RPR', 'refresh', function(frm) {
	// frappe.ui.form.on('rpr_list',{
	// 	'employee_full_name': function(frm){
	// 		frm.add_fetch("employee_full_name","employee_name","Amnaaa");
	// 	}
	// });
	// refresh: function(frm) {
		
	// }
});
// frappe.ui.form.on("[PARENT_DOCTYPE_TARGET]", "refresh", function(frm) {	
// 	frappe.ui.form.on("[CHILD_TABLE_TARGET_DOCTYPE]", {
// 			"[CHILD_TABLE_LINK FIELD]": function(frm) {
// 			frm.add_fetch("[CHILD_TABLE_LINK FIELD]", "[SOURCE_CUSTOM_FIELD2]", "[TARGET_CUSTOM_FIELD2]");
// 		}
// 	});

// });
// var set_required_list = function(frm) {
// 	frm.clear_table("rpr_list");
// 	if(frm.doc.work_permit_type && frm.doc.employee){
// 		frappe.call({
// 			doc: frm.doc,
// 			method: 'get_required_list',
// 			callback: function(r) {
// 				frm.refresh_field('rpr_list');
// 			},
// 			freeze: true,
// 			freeze_message: __('Fetching Data.')
// 		});
//   }
// 	frm.refresh_field('rpr_list');
// };