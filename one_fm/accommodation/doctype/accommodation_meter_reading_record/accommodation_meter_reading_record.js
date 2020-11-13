// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Accommodation Meter Reading Record', {
	refresh: function(frm) {
		set_filters(frm);
	},
	reference_doctype: function(frm) {
		set_filters(frm);
		frm.set_value('reference_name', '');
	},
	reference_name: function(frm) {
		set_filters(frm);
		set_meter(frm);
	},
	meter_type: function(frm) {
		set_filters(frm);
		set_meter(frm);
	},
	meter_reference: function(frm) {
		set_meter_details(frm);
	},
	last_reading: function(frm) {
		calculate_consumption(frm);
	},
	current_reading: function(frm) {
		calculate_consumption(frm);
	}
});

var calculate_consumption = function(frm) {
	if(frm.doc.last_reading && frm.doc.current_reading){
		frm.set_value('consumption', frm.doc.current_reading - frm.doc.last_reading)
	}
};

var set_meter = function(frm) {
	if(frm.doc.meter_type && frm.doc.reference_name){
		frappe.call({
			method: 'one_fm.accommodation.doctype.accommodation_meter_reading_record.accommodation_meter_reading_record.get_accommodation_meter',
			args: {
				'meter_type': frm.doc.meter_type,
				'reference_doctype': frm.doc.reference_doctype,
				'reference_name': frm.doc.reference_name
			},
			callback: function(r) {
				if(r && r.message && r.message.meter_reference){
					frm.set_value('meter_reference', r.message.meter_reference);
				}
				else{
					frm.set_value('meter_reference', '');
				}
			}
		});
	}
	else{
		frm.set_value('meter_reference', '');
	}
};

var set_meter_details = function(frm) {
	if(frm.doc.meter_reference){
		var filters = {'meter_reference': frm.doc.meter_reference};
		if(frm.doc.reference_doctype && frm.doc.reference_name){
			filters['reference_doctype'] = frm.doc.reference_doctype;
			filters['reference_name'] = frm.doc.reference_name;
		}
		frappe.call({
			method: 'one_fm.accommodation.doctype.accommodation_meter_reading_record.accommodation_meter_reading_record.get_accommodation_meter_details',
			args: filters,
			callback: function(r) {
				if(r && r.message){
					if(r.message.meter){
						frm.set_value('reading_uom', r.message.meter.default_reading_uom);
					}
					else{
						frm.set_value('reading_uom', '');
					}
					if(r.message.reading){
						var reading = r.message.reading;
						frm.set_value('last_reading_date', reading.last_reading_date);
						frm.set_value('last_reading', reading.last_reading);
						if(!frm.doc.reference_name){
							frm.set_value('reference_doctype', reading.parenttype);
							frm.set_value('reference_name', reading.parent);
						}
					}
					else{
						frm.set_value('last_reading_date', '');
						frm.set_value('last_reading', '');
					}
				}
				else{
					frm.set_value('reading_uom', '');
					frm.set_value('last_reading_date', '');
					frm.set_value('last_reading', '');
				}
			}
		});
	}
	else{
		frm.set_value('reading_uom', '');
		frm.set_value('last_reading_date', '');
		frm.set_value('last_reading', '');
	}
};

var set_filters = function(frm) {
		var reference_doctype = 'Accommodation';
		if(frm.doc.reference_doctype == 'Accommodation Unit'){
			reference_doctype = 'Accommodation Unit';
		}
		var filters = {};
		if(frm.doc.meter_type){
			filters['meter_type']=frm.doc.meter_type;
		}
		if(frm.doc.reference_name && frm.doc.reference_doctype){
			filters['reference_doctype'] = frm.doc.reference_doctype;
			filters['reference_name'] = frm.doc.reference_name;
		}
		if(filters){
			frm.set_query("meter_reference", function() {
				return {
					query: "one_fm.accommodation.doctype.accommodation_meter_reading_record.accommodation_meter_reading_record.filter_meter_ref",
					filters: filters
				}
			});
		}
};
