// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bed', {
	refresh: function(frm) {
		set_qr_code(frm);
		frm.set_query('accommodation_space', function () {
			return {
				filters: {
					'bed_space_available': 1
				}
			};
		});
		if(!frm.is_new() && frm.doc.status == 'Vacant'){
			var book_bed_btn = frm.add_custom_button(__('Book Bed'), function() {
				book_bed(frm);
			});
			book_bed_btn.addClass('btn-primary');
		}
	}
});

var book_bed = function(frm) {
  frappe.route_options = {"bed": frm.doc.name};
	frappe.new_doc("Book Bed");
};

var set_qr_code = function(frm) {
	let qr_code_html = `{%if doc.name%}
	<div style="display: inline-block;padding: 5%;">
	<div class="qr_code_print" id="qr_code_print">
		<img src="https://barcode.tec-it.com/barcode.ashx?code=MobileQRCode&multiplebarcodes=false&translate-esc=false&data={{doc.name}}&unit=Fit&dpi=150&imagetype=Gif&rotation=0&color=%23000000&bgcolor=%23ffffff&codepage=&qunit=Mm&quiet=2.5&eclevel=H" alt="">
		<p>
			{{qr_details}}
		</p>
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
	var doc = frm.doc;
	var qr_details = __('{0}, {1}<br/>{2} Floor, Unit: {3}<br/>{4} - {5}<br/>{6} Bed for {7}<br/>Code: {8}', [doc.accommodation_name,
		doc.type, doc.floor_name, doc.accommodation_unit, doc.accommodation_space_type,
		doc.bed_space_type, doc.bed_type, doc.gender, doc.name])
	var qr_code = frappe.render_template(qr_code_html,{"doc":doc, "qr_details": qr_details});
	$(frm.fields_dict["bed_qr"].wrapper).html(qr_code);
	refresh_field("bed_qr")
};
