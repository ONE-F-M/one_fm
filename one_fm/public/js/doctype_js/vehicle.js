frappe.ui.form.on('Vehicle', {
	refresh(frm) {
		set_qr_code(frm);
		frappe.breadcrumbs.add("GSD");
		frm.set_df_property('license_plate', 'hidden', false);
	},
	one_fm_vehicle_category(frm) {
	    if(frm.doc.one_fm_vehicle_category == 'Leased'){
	        frm.set_df_property('vehicle_leasing_contract', 'reqd', true);
	    }
	    else{
	        frm.set_df_property('vehicle_leasing_contract', 'reqd', false);
	    }
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
	}
})

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
