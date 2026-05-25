// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Maintenance Holiday List", {
	onload: function (frm) {
		// Fetch supported countries for the autocomplete field
		if (!frm.__countries_fetched) {
			frappe.call({
				method: "one_fm.one_fm.doctype.maintenance_holiday_list.maintenance_holiday_list.get_supported_countries",
				callback: function (r) {
					if (r && r.message) {
						frm.__supported_countries = r.message;
						set_country_options(frm, r.message);
					}
				},
			});
			frm.__countries_fetched = true;
		}
	},

	country: function (frm) {
		// When country changes, update subdivision options
		if (frm.__supported_countries) {
			set_subdivision_options(frm, frm.__supported_countries);
		}
		frm.set_value("subdivision", "");
	},
});

function set_country_options(frm, data) {
	var countries = data.countries || [];
	var options = countries.map(function (c) {
		return c.label;
	});
	frm.fields_dict.country.set_data(options);
}

function set_subdivision_options(frm, data) {
	var subdivisions_by_country = data.subdivisions_by_country || {};
	var country = frm.doc.country;

	// Find the country code from the label
	var country_code = null;
	var countries = data.countries || [];
	for (var i = 0; i < countries.length; i++) {
		if (countries[i].label === country) {
			country_code = countries[i].value;
			break;
		}
	}

	if (country_code && subdivisions_by_country[country_code]) {
		var subdivisions = subdivisions_by_country[country_code];
		frm.fields_dict.subdivision.set_data(subdivisions);
	} else {
		frm.fields_dict.subdivision.set_data([]);
	}
}
