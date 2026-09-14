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
 * added or by whom. The remark is asked for, saved, and only then is the menu item's own
 * handler allowed to run.
 *
 * The map refuses the transition on its own when the remark is empty (Gateway_1o50p1k
 * routes straight back to the PRO's task) and so does the controller. This is the third of
 * the three guards and the only one the PRO ever sees.
 */

frappe.provide("one_fm.visa_cancellation");

(function () {
	"use strict";

	const DOCTYPE = "Visa Cancellation Request";
	const PRO_STATE = "Pending by PRO";
	const CANCEL_ACTION = "Cancel";
	const REMARK = "pro_officer_rejection_remark";

	// Set on the menu item just before its own handler is re-fired, so the listener below
	// steps aside for that one click instead of asking for the remark all over again.
	const LET_THROUGH = "oneFmRemarkCaptured";

	/** The injected "Cancel" menu item this click landed on, if it is that one. */
	function cancel_action_item(event) {
		// The marker one_bpmn stamps on its own <li>. Frappe's native Cancel (docstatus)
		// carries no marker, and is not this action.
		const link = event.target.closest && event.target.closest("li[data-bpmn-action] a");
		if (!link) {
			return null;
		}

		return (link.textContent || "").trim() === __(CANCEL_ACTION) ? link : null;
	}

	function ask_for_remark(frm, link) {
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
					ask_for_remark(frm, link);
					return;
				}

				frm.set_value(REMARK, remark);
				frm.save().then(function () {
					// Hand the click back to one_bpmn rather than calling its engine here:
					// the menu item still holds the task it was built for, and re-fired it
					// applies the action exactly as it would have without this dialog.
					link.dataset[LET_THROUGH] = "1";
					$(link).trigger("click");
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

			const link = cancel_action_item(event);
			if (!link) {
				return;
			}

			if (link.dataset[LET_THROUGH]) {
				delete link.dataset[LET_THROUGH];
				return;
			}

			// Capture phase: stop it before one_bpmn's own handler sees it at all.
			event.preventDefault();
			event.stopPropagation();
			event.stopImmediatePropagation();

			ask_for_remark(frm, link);
		},
		true
	);
})();
