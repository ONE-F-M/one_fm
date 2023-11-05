// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Accommodation Unit', {
	refresh: function(frm) {
		set_qr_code(frm);
	}
});

var set_qr_code = function(frm) {
	let qr_code_html = `{%if doc.name%}
	<div style="display: inline-block;padding: 5%;">
	<div class="qr_code_print" id="qr_code_print">
	<img src="https://barcode.tec-it.com/barcode.ashx?code=MobileQRCode&multiplebarcodes=false&translate-esc=false&data={{url}}&unit=Fit&dpi=150&imagetype=Gif&rotation=0&color=%23000000&bgcolor=%23ffffff&codepage=&qunit=Mm&quiet=2.5&eclevel=H" alt="">
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
	</script>`
	var doc = frm.doc;
	var url = frappe.urllib.get_full_url("/api/method/one_fm.accommodation.utils.accommodation_qr_code_live_details?"
		+ "docname=" + encodeURIComponent(doc.name))
	var qr_details = __('{0}<br/>{1}, {2} Floor<br/>Owner Reference: {3}<br/>Code: {4}', [doc.accommodation_name,
		doc.type, doc.floor_name, doc.owner_reference_number, doc.name])
	var qr_code = frappe.render_template(qr_code_html,{"doc":doc, "qr_details": qr_details, "url": url});
	$(frm.fields_dict["unit_qr"].wrapper).html(qr_code);
	refresh_field("unit_qr")
};
