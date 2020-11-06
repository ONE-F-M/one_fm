// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Accommodation Meter Reading Record', {
	refresh: function(frm) {
		set_filters(frm);
	},
	reference_doctype: function(frm) {
		set_filters(frm);
	},
	reference_name: function(frm) {
		set_filters(frm);
	},
	meter_type: function(frm) {
		set_filters(frm);
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

var set_meter_details = function(frm) {
	if(frm.doc.meter_reference){
		frappe.call({
			method: 'one_fm.accommodation.doctype.accommodation_meter_reading_record.accommodation_meter_reading_record.get_accommodation_meter_details',
			args: {
				'meter_reference': frm.doc.meter_reference,
				'reference_doctype': frm.doc.reference_doctype,
				'reference_name': frm.doc.reference_name
			},
			callback: function(r) {
				if(r && r.message){
					if(r.message.meter){
						frm.set_value('reading_uom', r.message.meter.default_reading_uom);
					}
					if(r.message.reading){
						var reading = r.message.reading;
						frm.set_value('last_reading_date', reading.last_reading_date);
						frm.set_value('last_reading', reading.last_reading);
					}
				}
			}
		});
	}
};

var set_filters = function(frm) {
	var reference_doctype = 'Accommodation';
	if(frm.doc.reference_doctype == 'Accommodation Unit'){
		reference_doctype = 'Accommodation Unit';
	}
	frm.set_query("meter_reference", function() {
		return {
			query: "one_fm.accommodation.doctype.accommodation_meter_reading_record.accommodation_meter_reading_record.filter_meter_ref",
			filters: {'reference_doctype': reference_doctype, 'reference_name': frm.doc.reference_name, 'meter_type': frm.doc.meter_type}
		}
	});
};
