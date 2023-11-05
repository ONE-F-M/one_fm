// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Training Evaluation Form', {
	refresh: function(frm){
		if(!frm.doc.__islocal){
			frm.add_custom_button(
				'Get Form Link',
				() => {
					copyToClipboard(`${frappe.urllib.get_base_url()}/${frm.doc.route}`);
					frappe.msgprint(`<b>Link</b>: <a href="${frappe.urllib.get_base_url()}/${frm.doc.route}" target="_blank">${frappe.urllib.get_base_url()}/${frm.doc.route}</a>`);
					frappe.show_alert("Link Copied.");
				}
			).addClass('btn-primary');		}
	},
	training_form_template: function(frm) {
		let {training_form_template} = frm.doc;
		if(training_form_template !== undefined){
			frappe.call({
				method:"frappe.client.get",
				args: {
					doctype: "Training Evaluation Form Template",
					name: training_form_template,
                },
				callback: function(r) {
					if(!r.exc) {
						let {questions} = r.message;
						console.log(questions);
						questions.forEach((question) => {
							let child_row = frappe.model.add_child(frm.doc, "questions");
							child_row.question = question.question;
						});
						frm.refresh_fields("questions");
					}
				}
			});
		}
	}
});

function copyToClipboard(text) {
    if (window.clipboardData && window.clipboardData.setData) {
        // IE specific code path to prevent textarea being shown while dialog is visible.
        return clipboardData.setData("Text", text); 

    } else if (document.queryCommandSupported && document.queryCommandSupported("copy")) {
        var textarea = document.createElement("textarea");
        textarea.textContent = text;
        textarea.style.position = "fixed";  // Prevent scrolling to bottom of page in MS Edge.
        document.body.appendChild(textarea);
        textarea.select();
        try {
            return document.execCommand("copy");  // Security exception may be thrown by some browsers.
        } catch (ex) {
            console.warn("Copy to clipboard failed.", ex);
            return false;
        } finally {
            document.body.removeChild(textarea);
        }
    }
}   