// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt
/**
 * WI-002427: ask the PRO Officer why, at the moment they cancel.
 *
 * "Cancel" is not a Frappe Workflow button. It is one of the two actions the Visa
 * Cancellation process map puts on the PRO's user task, injected into the Actions menu by
 * one_bpmn on every form refresh (bpmn_form_actions.js). one_bpmn offers no hook to run
 * something before one of its actions, so the click is caught on the way down instead -
 * a capture-phase listener on the document, which does not care when the menu item was
 * added or by whom.
 *
 * The remark is saved before the action is applied, because the map's gateway
 * ("Is Cancellation Reason set ?") reads pro_officer_rejection_remark off the document
 * rather than off the click. An unsaved value routes the request straight back here.
 *
 * The map refuses the transition on its own when the remark is empty, and so does the
 * controller. This is the third of the three guards and the only one the PRO ever sees.
 */

frappe.provide("one_fm.visa_cancellation");

(function () {
	"use strict";

	const DOCTYPE = "Visa Cancellation Request";
	const PRO_STATE = "Pending by PRO";
	const CANCEL_ACTION = "Cancel";
	const REMARK = "pro_officer_rejection_remark";

	/** The injected "Cancel" menu item this click landed on, if it is that one. */
	function is_cancel_action_item(event) {
		// The marker one_bpmn stamps on its own <li>. Frappe's native Cancel (docstatus)
		// carries no marker, and is not this action.
		const link = event.target.closest && event.target.closest("li[data-bpmn-action] a");

		return !!link && (link.textContent || "").trim() === __(CANCEL_ACTION);
	}

	function offers_cancel(task) {
		if (Array.isArray(task.task_actions_detail) && task.task_actions_detail.length) {
			return task.task_actions_detail.some(function (detail) {
				return detail && detail.action === CANCEL_ACTION;
			});
		}

		return (task.task_actions || "").indexOf(CANCEL_ACTION) !== -1;
	}

	/**
	 * Complete the PRO's task with the Cancel action.
	 *
	 * The menu item's own handler cannot be re-used once the remark has been saved: saving
	 * refreshes the form, one_bpmn clears its injected items with jQuery .remove(), and that
	 * takes the click handler with them. The item on screen afterwards is a different
	 * element, injected asynchronously - so the task is fetched and completed here instead,
	 * through the same two API methods one_bpmn itself calls.
	 */
	function apply_cancel(frm) {
		return frappe
			.call({
				method: "one_bpmn.api.instance_api.get_active_bpmn_tasks",
				args: { doctype: frm.doctype, docname: frm.docname },
				freeze: true,
				freeze_message: __("Applying action…"),
			})
			.then(function (r) {
				const task = (r.message || []).find(offers_cancel);

				if (!task) {
					frappe.msgprint({
						title: __("Task Not Completed"),
						message: __(
							"This request has no Cancel action waiting on it any more. Refresh the page to see where it stands."
						),
						indicator: "red",
					});
					return;
				}

				return frappe
					.call({
						method: "one_bpmn.api.instance_api.complete_task",
						args: {
							instance_name: task.instance_name,
							task_id: task.task_id,
							data: JSON.stringify({ action: CANCEL_ACTION }),
						},
						freeze: true,
						freeze_message: __("Applying action…"),
					})
					.then(function () {
						frappe.show_alert(
							{
								message: __("{0} action applied successfully", [__(CANCEL_ACTION)]),
								indicator: "green",
							},
							4
						);
						frm.reload_doc();
					});
			});
	}

	function ask_for_remark(frm) {
		frappe.prompt(
			{
				fieldname: REMARK,
				fieldtype: "Small Text",
				label: __("PRO Officer Rejection Remark"),
				reqd: 1,
				default: frm.doc[REMARK] || "",
			},
			function (values) {
				const remark = (values[REMARK] || "").trim();

				// reqd already refuses an empty box; this catches a boxful of spaces, which
				// would otherwise be saved and read as a reason by everything downstream.
				if (!remark) {
					frappe.msgprint({
						title: __("Cancellation Reason Required"),
						message: __("Enter the reason for cancelling this request."),
						indicator: "red",
					});
					ask_for_remark(frm);
					return;
				}

				frm.set_value(REMARK, remark)
					.then(function () {
						// A retry with the same reason leaves nothing to save, and frm.save()
						// answers that with "No changes in the document" and rejects - which
						// would strand the action behind a dialog the PRO has already filled in.
						return frm.is_dirty() ? frm.save() : null;
					})
					.then(function () {
						return apply_cancel(frm);
					});
			},
			__("Reason for Cancelling"),
			__("Cancel Request")
		);
	}

	document.addEventListener(
		"click",
		function (event) {
			const frm = window.cur_frm;
			if (!frm || frm.doctype !== DOCTYPE || frm.is_new()) {
				return;
			}
			if (frm.doc.workflow_state !== PRO_STATE) {
				return;
			}
			if (!is_cancel_action_item(event)) {
				return;
			}

			// Capture phase: stop it before one_bpmn's own handler sees it at all.
			event.preventDefault();
			event.stopPropagation();
			event.stopImmediatePropagation();

			ask_for_remark(frm);
		},
		true
	);
})();
