// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Accommodation Meter Reading Record', {
	refresh: function(frm) {
		set_filters(frm);
		set_reading_month(frm);
	},
	accommodation: function(frm) {
		set_filters(frm);
		frm.set_value('accommodation_unit', '');
		set_meter(frm);
	},
	accommodation_unit: function(frm) {
		set_filters(frm);
		set_meter(frm);
	},
	reading_type: function(frm) {
		set_filters(frm);
		if(frm.doc.reading_type == 'Unit'){
			frm.set_df_property('accommodation_unit', 'reqd', true);
		}
		else{
			frm.set_value('accommodation_unit', '');
			frm.set_df_property('accommodation_unit', 'reqd', false);
		}
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
	},
	reading_date: function(frm) {
		set_reading_month(frm);
	}
});

var set_reading_month = function(frm) {
	if(frm.doc.reading_date){
		var months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
		var month = months[moment(frm.doc.reading_date).get('month')]
		if(month != frm.doc.month){
			frm.set_value('month', month);
		}
	}
}

var calculate_consumption = function(frm) {
	if(frm.doc.last_reading && frm.doc.current_reading){
		frm.set_value('consumption', frm.doc.current_reading - frm.doc.last_reading)
	}
};

var set_meter = function(frm) {
	if(frm.doc.meter_type && frm.doc.reading_type){
		var reference_doctype = '';
		var reference_name = '';
		if(frm.doc.reading_type == 'Unit' && frm.doc.accommodation_unit){
			reference_doctype = 'Accommodation Unit';
			reference_name = frm.doc.accommodation_unit;
		}
		else if(frm.doc.reading_type == 'Common' && frm.doc.accommodation){
			reference_doctype = 'Accommodation';
			reference_name = frm.doc.accommodation;
		}
		if(reference_name && reference_doctype){
			frappe.call({
				method: 'one_fm.accommodation.doctype.accommodation_meter_reading_record.accommodation_meter_reading_record.get_accommodation_meter',
				args: {
					'meter_type': frm.doc.meter_type,
					'reference_doctype': reference_doctype,
					'reference_name': reference_name
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
	}
	else{
		frm.set_value('meter_reference', '');
	}
};

var set_meter_details = function(frm) {
	if(frm.doc.meter_reference){
		frappe.call({
			method: 'one_fm.accommodation.doctype.accommodation_meter_reading_record.accommodation_meter_reading_record.get_accommodation_meter_details',
			args: {'meter_reference': frm.doc.meter_reference},
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
						if(reading.parenttype == 'Accommodation' && !frm.doc.accommodation){
							frm.set_value('accommodation', reading.parent);
							if(!frm.doc.reading_type){
								frm.set_value('reading_type', 'Common');
							}
						}
						if(reading.parenttype == 'Accommodation Unit' && !frm.doc.accommodation_unit){
							frm.set_value('accommodation_unit', reading.parent);
							if(!frm.doc.reading_type){
								frm.set_value('reading_type', 'Unit');
							}
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
	var filters = {};
	if(frm.doc.reading_type == 'Unit' && frm.doc.accommodation_unit){
		filters['reference_doctype'] = 'Accommodation Unit';
		filters['reference_name'] = frm.doc.accommodation_unit;
	}
	else if(frm.doc.reading_type == 'Common' && frm.doc.accommodation){
		filters['reference_doctype'] = 'Accommodation';
		filters['reference_name'] = frm.doc.accommodation;
	}
	if(frm.doc.meter_type){
		filters['meter_type']=frm.doc.meter_type;
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
