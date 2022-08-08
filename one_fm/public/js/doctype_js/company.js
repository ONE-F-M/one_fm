frappe.ui.form.on('Company', {
	notify_live_users: function(frm){
		var users = []
		if(frappe.user.has_role('System Manager')){
			if(frm.doc.live_user_notification_message){
				if(!frm.is_dirty()){
					if(frm.doc.notify){
						frm.doc.notify.forEach((item) => {
							users.push(item.recipient)
						});
					}
					frappe.call({
						method: 'one_fm.utils.notify_live_user',
						args: {
							company: frm.doc.name,
							message: frm.doc.live_user_notification_message,
							users: users
						},
						callback: function(r) {
							if(!r.exc) {
								frm.reload_doc();
							}
						},
						freeze: true,
						freeze_message: (__("Notifiying the live users..!!"))
					});
				}
				else{
					frappe.msgprint(__("Please Update the Document."))
				}
			}
			else{
				frappe.msgprint(__("Add a Live User Notification Message befor you notify!!"));
			}
		}
		else{
			frappe.msgprint(__("System Manger can only send the notification!!"));
		}
	}
});
