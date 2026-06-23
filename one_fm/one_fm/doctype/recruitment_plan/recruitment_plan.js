// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Recruitment Plan", {
	setup: function(frm) {
		frm.set_query("erf", function() {
			if (!frm.doc.designation) {
				return {
					filters: {
						name: ["in", []] // Show nothing if no designation is selected
					}
				};
			}
			return {
				filters: {
					docstatus: 1,
					status: "Accepted",
					designation: frm.doc.designation
				}
			};
		});
	},
	refresh: function(frm) {
		loadRecruitmentPlanAutocompleteOptions(frm);
		toggleCountryLabel(frm);
	},
	designation: function(frm) {
		// Reset ERF if it does not match the new designation
		if (frm.doc.erf) {
			frappe.db.get_value("ERF", frm.doc.erf, "designation", (r) => {
				if (r && r.designation !== frm.doc.designation) {
					frm.set_value("erf", "");
				}
			});
		}
	},
	recruitment_plan_type: function(frm) {
		toggleCountryLabel(frm);
	}
});

function toggleCountryLabel(frm) {
	if (frm.doc.recruitment_plan_type === "Recruitment Trip") {
		frm.set_df_property("trip_country", "label", "Trip Country");
	} else {
		frm.set_df_property("trip_country", "label", "Country");
	}
}

function populateAutocomplete(frm, fieldname, options) {
	let field = frm.fields_dict[fieldname];
	if (!field) return;
	if (field.get_query) delete field.get_query;

	setTimeout(() => {
		let f = frm.fields_dict[fieldname];
		if (f && typeof f.set_data === "function") {
			f.set_data(options);
		}
	}, 0);
}

function loadRecruitmentPlanAutocompleteOptions(frm) {
	const COUNTRY_KEY = "__recruitment_plan_country_options";
	const NATIONALITY_KEY = "__recruitment_plan_nationality_options";

	if (frappe[COUNTRY_KEY] && frappe[NATIONALITY_KEY]) {
		populateAutocomplete(frm, "trip_country", frappe[COUNTRY_KEY]);
		populateAutocomplete(frm, "nationality_in_pr_request", frappe[NATIONALITY_KEY]);
		return;
	}

	frappe.call({
		method: "one_fm.one_fm.doctype.recruitment_plan.recruitment_plan.get_autocomplete_options",
		callback: function(r) {
			if (r.message) {
				let countries = ["Any", "African", "Asian"];
				(r.message.countries || []).forEach(c => {
					if (!countries.includes(c)) {
						countries.push(c);
					}
				});
				frappe[COUNTRY_KEY] = countries;
				populateAutocomplete(frm, "trip_country", countries);

				let nationalities = ["Any", "African", "Asian"];
				(r.message.nationalities || []).forEach(n => {
					if (!nationalities.includes(n)) {
						nationalities.push(n);
					}
				});
				frappe[NATIONALITY_KEY] = nationalities;
				populateAutocomplete(frm, "nationality_in_pr_request", nationalities);
			}
		}
	});
}
