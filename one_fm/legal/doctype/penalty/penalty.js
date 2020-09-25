// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Penalty', {
	refresh: function(frm){
		$('.actions-btn-group').hide();
		
		frm.fields_dict["penalty_details"].grid.set_column_disp(["period_start_date"], 0);
		frm.fields_dict["penalty_details"].grid.set_column_disp(["period_lapse_date"], 0);

        frm.fields_dict["penalty_details"].grid.toggle_enable(["penalty_levied"], 0);
        frm.fields_dict["penalty_details"].grid.toggle_enable(["penalty_type"], 0);
        frm.fields_dict["penalty_details"].grid.toggle_enable(["exact_notes"], 0);
        frm.fields_dict["penalty_details"].grid.toggle_enable(["attachments"], 0);
		
		if(frm.doc.workflow_state == "Penalty Accepted" && frm.doc.verified == 0){
			frm.add_custom_button(
				'Create Legal Investigation',
				() => {
					let {doctype, docname} = frm;
					frappe.xcall('one_fm.legal.doctype.penalty.penalty.create_legal_inv',{doctype, docname})
					.then(res => console.log(res));
				}
			).addClass('btn-info');
		}
		if(frm.doc.workflow_state == "Penalty Issued" && frm.doc.recipient_user == frappe.session.user){
			frm.add_custom_button(
				'Accept Penalty',
				() => {
					let d = new frappe.ui.Dialog({
						'title': 'Accept Penalty with Face Recognition.',
						'fields': [
							{'label': 'Tries Left', 'fieldname': 'retries', 'fieldtype': 'Int', 'read_only': 1, 'default': frm.doc.retries},
							{'fieldtype': 'Section Break', 'fieldname': 'sb1'},
							{'fieldname': 'wrapper', 'fieldtype': 'HTML'},
						],
						primary_action: function(){
							let canvas, ctx;

							// Get the canvas and obtain a context for
							// drawing in it
							canvas =  $(d.fields_dict.wrapper.$wrapper).find("#myCanvas")[0];
							console.log(preview, canvas, canvas.height, canvas.width);
							ctx = canvas.getContext('2d');
						
							// Draws current image from the video element into the canvas
							ctx.drawImage(preview, 0,0, canvas.width, canvas.height);
							let imgUrl = canvas.toDataURL("image/png");
							console.log(ctx, imgUrl);

							recorder.stop(); 
							stop_cam(preview);
							console.log(frm.doc.retries);
							verify_accept(imgUrl.split(",")[1], frm.doc.retries, frm.doc.name, d, frm);
						},
						hide: function(){
							stop_cam(preview);
							console.log(stop_cam, preview);
								// super.set_secondary_action();
							// d.hide()
						}
					});
					d.fields_dict.wrapper.$wrapper.append('<video id="preview" height="350" autoplay muted text-center></video><canvas style="display:none;" id="myCanvas" width="400" height="350"></canvas>');
					d.show();
					d.$wrapper.find('.modal-dialog').css('width', '50%');
					load_camera(d);
				}
			).addClass('btn-primary');
			frm.add_custom_button(
				'Reject Penalty',
				() => {
					let rejection_dialog = new frappe.ui.Dialog({
						'fields': [
							{'fieldname': 'ht', 'fieldtype': 'HTML'},
							{'fieldname': 'rejection_reason', 'fieldtype': 'Small Text', 'label': 'Reason for Rejection'},							
						],
						primary_action: function(){
							rejection_dialog.hide();
							// show_alert(rejection_dialog.get_values());
							console.log(rejection_dialog.get_values());
							let {rejection_reason} = rejection_dialog.get_values();
							// frappe.model.set_value(frm.doctype, frm.docname, "reason_for_rejection", rejection_reason);
							frappe.xcall('one_fm.legal.doctype.penalty.penalty.reject_penalty', {rejection_reason, docname: frm.doc.name})
							.then(res => frm.reload_doc());
						}
					});
					let rejection_warning = `
						<div class="alert alert-danger">
							<p>
								Note: On rejecting the penalty, Company will open up an investigation and you will be stopped from work because of the investigation and all days of the investigation will not be paid if you are found to be at fault at the conclusion of investigation.
							</p> 
						</div>
					`;
					rejection_dialog.fields_dict.ht.$wrapper.html(rejection_warning);
					rejection_dialog.show();
				}
			).addClass('btn-danger');;
		}
	}
});

function load_camera(d){
	window.preview = $(d.fields_dict.wrapper.$wrapper).find('#preview')[0];
	navigator.mediaDevices.getUserMedia({
		video: {
			width: { ideal: 1024 },
			height: { ideal: 768 },
			frameRate: {ideal: 5, max: 10},
			facingMode: 'user'
		},
		audio: false
	})
	.then((stream) => {			
		window.localStream = stream;
		preview.srcObject = stream;
		preview.captureStream = preview.captureStream || preview.mozCaptureStream;
		return new Promise(resolve => preview.onplaying = resolve);
	})
	.then(() => {
		window.recorder = new MediaRecorder(preview.captureStream());
		let data = [];

		recorder.ondataavailable = event => data.push(event.data);
		recorder.start();

		let stopped = new Promise((resolve, reject) => {
			recorder.onstop = resolve;
			recorder.onerror = event => reject(event.name);
		});

		return Promise.all([ stopped ]).then(() => data);
	})
}


function verify_accept(file, retries, docname, d, frm){
	frappe.xcall('one_fm.legal.doctype.penalty.penalty.accept_penalty',{
		file, retries, docname
	}).then(res => {
		console.log(res);
		if(res.message == "error" && res.retries > 0){
			let {retries} = res;
			frappe.msgprint(__(`Face verification did not succeed. You have ${retries} retries left.`));
			frappe.model.set_value(frm.doc.doctype, frm.doc.name, "retries", retries);
			d.set_value("retries", retries);
			frm.reload_doc();
			load_camera(d);
		}
		else{
			d.hide();
			frm.reload_doc();
		}
	})
}


function stop_cam(videoEl){
	localStream.getTracks().forEach( (track) => {
		track.stop();	
	});
	// stop only video
	localStream.getVideoTracks()[0].stop();
	videoEl.srcObject = null;
}