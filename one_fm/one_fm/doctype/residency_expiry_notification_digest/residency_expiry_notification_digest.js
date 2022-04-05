// Copyright (c) 2022, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Residency Expiry Notification Digest', {
	refresh: function(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__('View Now'), function() {
				frappe.call({
					method: 'one_fm.one_fm.doctype.residency_expiry_notification_digest.residency_expiry_notification_digest.get_digest_msg',
					args: {
						name: frm.doc.name
					},
					callback: function(r) {
						let d = new frappe.ui.Dialog({
							title: __('Residency Expiry Notification Digest', [frm.doc.name]),
							width: 800
						});
						$(d.body).html(r.message);
						d.show();
					}
				});
			});

			frm.add_custom_button(__('Send Now'), function() {
				return frm.call('send', null, () => {
					frappe.show_alert({ message: __("Message Sent"), indicator: 'green'});
				});
			});
		}
	}
});
