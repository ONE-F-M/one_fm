// Copyright (c) 2023, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Subcontract Staff Shortlist', {
	refresh: function(frm) {
	},
	set_full_name:function(frm,cdt,cdn,lang){
		let row = locals[cdt][cdn]
		if(lang =='en'){
			let name_array = [row.first_name,row.second_name,row.third_name,row.fourth_name,row.last_name]
			row.full_name = name_array.join(' ')
		}
		else{
			let name_array = [row.first_name_in_arabic,row.second_name_in_arabic,row.third_name_in_arabic,row.fourth_name_in_arabic,row.last_name_in_arabic]
			row.full_name_in_arabic = name_array.join(' ')
		}
		frm.refresh_fields()
	},
	default_designation: function(frm) {
		$.each(frm.doc.subcontract_staff_shortlist_detail || [], function(i, item) {
			frappe.model.set_value('Subcontract Staff Shortlist Detail', item.name, 'designation', frm.doc.default_designation);
		});
	}
});


frappe.ui.form.on('Subcontract Staff Shortlist Detail', {
	first_name:function(frm,cdt,cdn){
		frm.events.set_full_name(frm,cdt,cdn,'en')
	},
	second_name:function(frm,cdt,cdn){
		frm.events.set_full_name(frm,cdt,cdn,'en')
	},
	third_name:function(frm,cdt,cdn){
		frm.events.set_full_name(frm,cdt,cdn,'en')
	},
	fourth_name:function(frm,cdt,cdn){
		frm.events.set_full_name(frm,cdt,cdn,'en')
	},
	last_name:function(frm,cdt,cdn){
		frm.events.set_full_name(frm,cdt,cdn,'en')
	},
	first_name_in_arabic:function(frm,cdt,cdn){
		frm.events.set_full_name(frm,cdt,cdn,'ar')
	},
	second_name_in_arabic:function(frm,cdt,cdn){
		frm.events.set_full_name(frm,cdt,cdn,'ar')
	},
	third_name_in_arabic:function(frm,cdt,cdn){
		frm.events.set_full_name(frm,cdt,cdn,'ar')
	},
	fourth_name_in_arabic:function(frm,cdt,cdn){
		frm.events.set_full_name(frm,cdt,cdn,'ar')
	},
	last_name_in_arabic:function(frm,cdt,cdn){
		frm.events.set_full_name(frm,cdt,cdn,'ar')
	},
	subcontract_staff_shortlist_detail_add: function (frm, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		if (!row.designation) {
			frm.script_manager.copy_from_first_row("subcontract_staff_shortlist_detail", row, "designation");
		}
		if(!row.designation) row.designation = frm.doc.default_designation;
	}
});
