// Copyright (c) 2023, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Subcontract Staff Shortlist', {
	refresh: function(frm) {
		;
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
	}

});
