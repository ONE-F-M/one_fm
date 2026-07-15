frappe.ui.form.on('Vehicle', {
	refresh(frm) {
		set_qr_code(frm);
		frappe.breadcrumbs.add("GSD");
		frm.set_df_property('license_plate', 'hidden', false);
	},
	onload(frm) {
		if (frm.is_new() && !frm.doc.custom_naming_series) {
			frm.set_value("custom_naming_series", "VHL-.####");
		}
	},
	one_fm_vehicle_category(frm) {
		const series_map = {
			"Owned": "VHL-.####",
			"Leased": "VHL-L-.####",
			"Subcontractor": "VHL-S-.####"
		};
		const category = frm.doc.one_fm_vehicle_category;
		frm.set_value("custom_naming_series", series_map[category] || "VHL-.####");
		frm.set_df_property("vehicle_leasing_contract", "reqd", category === "Leased");
	},
	vehicle_leasing_contract(frm){
	  if(!frm.doc.vehicle_leasing_contract){
	      frm.set_value('vehicle_leasing_details', '');
	  }
	},
	vehicle_leasing_details(frm){
	    if(frm.doc.vehicle_leasing_details){
	        frappe.call({
	           method: "one_fm.fleet_management.doctype.vehicle_leasing_contract.vehicle_leasing_contract.get_vehicle_from_leasing_contract",
				args: {'vehicle_detail': frm.doc.vehicle_leasing_details},
				callback: function(r) {
					if(!r.exc){
					    var data = r.message;
					    frm.set_value('make', data.make);
					    frm.set_value('model', data.model);
					    frm.set_value('one_fm_vehicle_type', data.vehicle_type);
					    frm.set_value('one_fm_year_of_made', data.year_of_made);
					}
				},
				freeze: true,
				freeze_message: "Fetching Vehicle Details..."
	        });
	    }
	},
	employee(frm) {
		// A handover to a new custodian is logged the moment a new Employee is
		// selected. The row snapshots the current odometer (one_fm_milage) into
		// the hidden mileage_at_handover field. Clearing the Employee logs nothing.
		if (!frm.doc.employee) {
			return;
		}
		log_custodian_handover(frm);
	},
	custom_handover_date(frm) {
		// Keep the active custodian row's handover date aligned with the form
		// value if the date is set after the Employee was selected.
		let active_row = get_active_custodian_row(frm);
		if (active_row && active_row.employee_id === frm.doc.employee) {
			active_row.handover_date = frm.doc.custom_handover_date;
			frm.refresh_field("custom_vehicle_custodian_history");
		}
	},
	one_fm_milage(frm) {
		// The current mileage feeds the active custodian's covered distance.
		calculate_custodian_mileage(frm);
	}
})

var log_custodian_handover = function(frm) {
	let row = frm.add_child("custom_vehicle_custodian_history", {
		employee_id: frm.doc.employee,
		handover_date: frm.doc.custom_handover_date,
		mileage_at_handover: cint(frm.doc.one_fm_milage)
	});

	// Populate Employee Name immediately for display (also resolved on save via fetch_from).
	if (frm.doc.employee) {
		frappe.db.get_value("Employee", frm.doc.employee, "employee_name").then(r => {
			if (r && r.message) {
				row.employee_name = r.message.employee_name;
				frm.refresh_field("custom_vehicle_custodian_history");
			}
		});
	}

	frm.refresh_field("custom_vehicle_custodian_history");
	calculate_custodian_mileage(frm);
};

var get_active_custodian_row = function(frm) {
	let rows = frm.doc.custom_vehicle_custodian_history || [];
	return rows.length ? rows[rows.length - 1] : null;
};

var calculate_custodian_mileage = function(frm) {
	// Past rows:  next row's mileage_at_handover - this row's mileage_at_handover.
	// Active row: parent's current mileage (one_fm_milage) - this row's mileage_at_handover.
	let rows = frm.doc.custom_vehicle_custodian_history || [];
	let current_mileage = flt(frm.doc.one_fm_milage);

	rows.forEach(function(row, index) {
		let covered;
		if (index < rows.length - 1) {
			covered = flt(rows[index + 1].mileage_at_handover) - flt(row.mileage_at_handover);
		} else {
			covered = current_mileage - flt(row.mileage_at_handover);
		}
		row.mileage_covered = cint(covered);
	});

	frm.refresh_field("custom_vehicle_custodian_history");
};

var set_qr_code = function(frm) {
	let qr_code_html = `{%if doc.name%}
	<div style="display: inline-block;padding: 5%;">
	<div class="qr_code_print" id="qr_code_print">
		<img src="https://barcode.tec-it.com/barcode.ashx?code=MobileQRCode&multiplebarcodes=false&translate-esc=false&data={{doc.name}}&unit=Fit&dpi=150&imagetype=Gif&rotation=0&color=%23000000&bgcolor=%23ffffff&codepage=&qunit=Mm&quiet=2.5&eclevel=H" alt="">
	</div>
	<br>
	<input name="qr_b_print" type="button" class="qr_ipt" id="qr_ipt" value=" Print ">
	</div>
	{%endif%}
	<script type="text/javascript">
	$("#qr_ipt").click(function() {
	    var divToPrint = document.getElementById("qr_code_print");
	    newWin = window.open("");
	    newWin.document.write(divToPrint.outerHTML);
	    newWin.print();
	});
	</script>
	`
	var qr_code = frappe.render_template(qr_code_html, {"doc":frm.doc});
	$(frm.fields_dict["one_fm_vehicle_qr_code"].wrapper).html(qr_code);
	refresh_field("one_fm_vehicle_qr_code")
};
