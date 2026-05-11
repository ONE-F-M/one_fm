// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on('Site Transport Stop Location', {
    refresh: function (frm) {
        apply_location_filters(frm);
    },
    site_arrangement: function (frm) {
        apply_location_filters(frm);
    }
});

frappe.ui.form.on("Site To Location Mapping", {
	location: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.location) {
			frappe.db.get_value("Location", row.location, "governorate_area", function (r) {
				if (r && r.governorate_area) {
					frappe.model.set_value(cdt, cdn, "governorate_area", r.governorate_area);
					frappe.db.get_value("Governorate Area", r.governorate_area, "governorate", function (g) {
						if (g && g.governorate) {
							frappe.model.set_value(cdt, cdn, "governorate", g.governorate);
						}
					});
				} else {
					frappe.model.set_value(cdt, cdn, "governorate_area", "");
					frappe.model.set_value(cdt, cdn, "governorate", "");
				}
			});
		} else {
			frappe.model.set_value(cdt, cdn, "governorate_area", "");
			frappe.model.set_value(cdt, cdn, "governorate", "");
		}
	}
});

function apply_location_filters(frm) {
    // Filter the Link field for "One Location Many Sites" arrangement
    frm.set_query("transport_stop_location", function () {
        return {
            filters: [
                ["Location", "location_type", "=", "Stop Location"]
            ]
        };
    });

    // Filter the child table location field for "One Site Many Locations" arrangement
    frm.set_query("location", "transport_stop_locations", function () {
        return {
            filters: [
                ["Location", "location_type", "=", "Stop Location"]
            ]
        };
    });

    // Filter the 'site' Link field (in "One Site Many Locations")
    frm.set_query("site", function () {
        return {
            filters: [
                ["Operations Site", "status", "=", "Active"]
            ]
        };
    });

    // Filter 'sites' field in 'sites' child table (in "One Location Many Sites")
    frm.set_query("sites", "sites", function () {
        return {
            filters: [
                ["Operations Site", "status", "=", "Active"]
            ]
        };
    });
}
