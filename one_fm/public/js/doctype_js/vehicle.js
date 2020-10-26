frappe.ui.form.on('Vehicle', {
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
