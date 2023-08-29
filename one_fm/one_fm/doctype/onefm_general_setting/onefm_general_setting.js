// Copyright (c) 2022, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('ONEFM General Setting', {
	refresh: function(frm) {
		if(!frm.is_new()){
			frm.trigger('setup_face_recognition');
		}
	},
	setup_face_recognition(frm){
		frm.add_custom_button('Setup Face Recognition', ()=>{
			frappe.call({
				method: 'one_fm.api.utils.set_up_face_recognition_server_credentials'
			}).then(res=>{
				frappe.msgprint(res.message.message)
			})
		}, 'Actions')
		
	}
});
