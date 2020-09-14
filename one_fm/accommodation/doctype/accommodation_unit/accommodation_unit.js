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
	<img src="https://barcode.tec-it.com/barcode.ashx?code=MobileQRCode&multiplebarcodes=false&translate-esc=false&data={{doc.name}}&unit=Fit&dpi=150&imagetype=Gif&rotation=0&color=%23000000&bgcolor=%23ffffff&codepage=&qunit=Mm&quiet=2.5&eclevel=H" alt="">
	</div>
	</div>
	{%endif%}`
	var qr_code = frappe.render_template(qr_code_html,{"doc":frm.doc});
	$(frm.fields_dict["unit_qr"].wrapper).html(qr_code);
	refresh_field("unit_qr")
};
