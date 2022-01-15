this.frm.dashboard.add_transactions([
    {
        'items': [
            'Customer Asset'
            
        ],
        'label': 'Related'
    },

]);

frappe.ui.form.on('Purchase Receipt', {
	status: function(frm){
		confirm_accept_approve_purchase_receipt(frm);
	}
});
var confirm_accept_approve_purchase_receipt = function(frm) {
	if(frm.doc.status == "Completed"){
		frappe.confirm(
			__('A one time code will be sent to you for verification in order to use your signature for approval. Do You Want to {0} this Request for Material?', [msg_status]),
			function(){
				// Yes
				var doctype = frm.doc.doctype
				var document_name = frm.doc.name
				frappe.xcall('one_fm.utils.send_verification_code', {doctype, document_name})
					.then(res => {
						console.log(res);
					}).catch(e => {
						console.log(e);
					})
				var d = new frappe.ui.Dialog({
					title : __("Approval verification"),
					fields : [
						{
							fieldtype: "Int",
							label: "Enter verification code sent to your email address",
							fieldname: "verification_code",
							reqd: 1,
							onchange: function(){
								let code = d.get_value('verification_code')
								if (!is_valid_verification_code(code)){frappe.throw(__("Invalid verification code."))}
							}
						},
						{
							fieldtype: "Button", 
							label: "Resend code", 
							fieldname: "resend_verification_code"
						},
						{
							fieldtype: "HTML",
							label: "Time remaining",
							fieldname: "timer"
						}
					],
					primary_action_label: __("Submit"),
					primary_action: function(){
						var verification_code = d.get_value('verification_code');
						frappe.xcall('one_fm.utils.verify_verification_code', {doctype, document_name, verification_code})
							.then(res => {
								if (res){
									d.hide()
									accept_approve_purchase_order(frm);
								} else{
									frappe.msgprint(__("Incorrect verification code. Please try again."));
								}
							})
					},
				});
				d.fields_dict.resend_verification_code.input.onclick = function() {
					reset_timer();
					frappe.xcall('one_fm.utils.send_verification_code', {doctype, document_name})
					.then(res => {
						console.log(res);
					}).catch(e => {
						console.log(e);
					})
				}
				start_timer(60*5, d);
				d.show();
			},
			function(){} // No
		);
	}
};

var timer;
function start_timer(duration, d) {
    timer = duration;
    var minutes, seconds;
    setInterval(function () {
        minutes = parseInt(timer / 60, 10)
        seconds = parseInt(timer % 60, 10);

        minutes = minutes < 10 ? "0" + minutes : minutes;
        seconds = seconds < 10 ? "0" + seconds : seconds;

        d.set_value('timer', "Verification code expires in: " + minutes + ":" + seconds);

        if (--timer < 0) {
            timer = duration;
        }
    }, 1000);
}

function reset_timer() {
  timer = 60 * 5;
}

var accept_approve_purchase_order = function(frm) {
	frappe.call({
		doc: frm.doc,
		method: 'one_fm.purchase.utils.accept_approve_purchase_receipt',
		args: {doc: frm.doc},
		callback(r) {
			if (!r.exc) {
				frm.reload_doc();
			}
		},
		freeze: true,
		freeze_message: __('Updating the Request..!')
	});
};
function is_valid_verification_code(code){
	const code_expression = /^\d{6}(\s*,\s*\d{6})*$/;
	if (code_expression.test(code))  return true;

	return false;
}