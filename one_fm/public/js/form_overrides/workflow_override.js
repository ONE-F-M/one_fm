// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// MIT License. See license.txt

class WorkflowActionOverride extends frappe.ui.form.States{
	show_actions() {
		var added = false;
		var me = this;

		// if the loaded doc is dirty, don't show workflow buttons
		if (this.frm.doc.__unsaved === 1) {
			return;
		}

		function has_approval_access(transition) {
			let approval_access = false;
			const user = frappe.session.user;
			if (
				user === "Administrator" ||
				transition.allow_self_approval ||
				user !== me.frm.doc.owner
			) {
				approval_access = true;
			}
			return approval_access;
		}

		function apply_workflow(d) {
			frappe
				.xcall("frappe.model.workflow.apply_workflow", {
					doc: me.frm.doc,
					action: d.action,
				})
				.then((doc) => {
					frappe.model.sync(doc);
					me.frm.refresh();
					me.frm.selected_workflow_action = null;
					me.frm.script_manager.trigger("after_workflow_action");
				})
				.finally(() => {
					frappe.dom.unfreeze();
				});
		}

		function confirm_to_apply_workflow(d){
			frappe.dom.unfreeze();
			let confirm_msg = __(d.custom_confirm_message) || __('Are you sure you want to proceed?')
			frappe.confirm(confirm_msg,
				() => {
					// Yes
					frappe.dom.freeze();
					// If the transition also requires a digital signature (DSS),
					// trigger the DSS acknowledgement before applying.
					if(d.require_digital_signature){
						trigger_digital_signature(d);
					}
					else{
						apply_workflow(d);
					}
				},
				() => {
					// No
				}
			)
		}

		// Trigger the Digital Signature Service (DSS) acknowledgement for
		// transitions flagged with require_digital_signature.
		// Mirrors the placeholder flow in one_bpmn; the actual signature capture
		// UI is a follow-up. On acknowledgement the workflow action is applied.
		function trigger_digital_signature(d){
			frappe.dom.unfreeze();
			frappe.confirm(
				__('<b>Digital Signature Required</b><br><br>' +
					'This action requires a digital signature to proceed. ' +
					'By clicking "Proceed", you acknowledge and authorize this action with your identity.'),
				() => {
					// Yes / Proceed
					frappe.dom.freeze();
					apply_workflow(d);
				},
				() => {
					// No
				}
			)
		}

		frappe.workflow.get_transitions(this.frm.doc).then((transitions) => {
			this.frm.page.clear_actions_menu();
			transitions.forEach((d) => {
				if (frappe.user_roles.includes(d.allowed) && has_approval_access(d)) {
					added = true;
					me.frm.page.add_action_item(__(d.action), function () {
						// set the workflow_action for use in form scripts
						frappe.dom.freeze();
						me.frm.selected_workflow_action = d.action;
						me.frm.script_manager.trigger("before_workflow_action").then(() => {
							if(d.custom_confirm_transition){
								confirm_to_apply_workflow(d);
							}
							else if(d.require_digital_signature){
								// Digital Signature Service (DSS) trigger
								trigger_digital_signature(d);
							}
							else{
								apply_workflow(d);
							}
						}).catch(() => {
							frappe.dom.unfreeze();
							me.frm.selected_workflow_action = null;
						});
					});
				}
			});

			this.setup_btn(added);
		});
	}
}

frappe.ui.form.States=WorkflowActionOverride
