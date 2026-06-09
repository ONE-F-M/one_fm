// Copyright (c) 2025, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Contract Compliance Checker", {
	onload: function(frm) {
		frm.trigger("render_take_action_buttons");
	},
	refresh: function(frm) {
		frm.trigger("render_take_action_buttons");
	},
	render_take_action_buttons: function(frm) {
		frappe.after_ajax(function() {
			setTimeout(function() {
				_inject_take_action_buttons(frm);
			}, 500);
		});
	}
});

function _handle_take_action(frm, idx) {
	let row = (frm.doc.items || [])[idx - 1];

	if (!row || !row.comment) {
		frappe.msgprint(__("No compliance issue found for this row."));
		return;
	}

	frappe.call({
		method: "one_fm.operations.doctype.contract_compliance_checker.contract_compliance_checker.get_take_action_data",
		args: {
			project: frm.doc.project,
			item: row.item,
			comment: row.comment,
			from_date: row.from_date,
			to_date: row.to_date
		},
		callback: function(r) {
			if (r.message && r.message.path) {
				let url = new URL(r.message.path, window.location.origin);
				let params = r.message.params || {};
				Object.entries(params).forEach(function([key, value]) {
					if (value) url.searchParams.set(key, value);
				});
				window.open(url.toString(), "_blank");
			} else {
				frappe.msgprint(__("Unable to determine the appropriate action for this item."));
			}
		}
	});
}

function _inject_take_action_buttons(frm) {
	let $grid_wrapper = frm.fields_dict.items.grid.wrapper;

	$grid_wrapper.find('[data-fieldname="take_action"]').each(function() {
		let $cell = $(this);
		let $static = $cell.find(".static-area");

		if (!$static.length) {
			$static = $cell;
		}

		// Skip if button already injected
		if ($static.find(".take-action-btn").length) return;

		let $row = $cell.closest("[data-idx]");
		let idx = parseInt($row.attr("data-idx"));
		let row_doc = (frm.doc.items || [])[idx - 1];

		if (!row_doc || !row_doc.comment) return;

		let $btn = $(
			'<button class="btn btn-xs btn-primary take-action-btn">'
			+ __("Take Action") + "</button>"
		);

		// Bind click directly on the button to prevent grid row activation
		$btn.on("click", function(e) {
			e.stopPropagation();
			e.stopImmediatePropagation();
			e.preventDefault();
			_handle_take_action(frm, idx);
			return false;
		});

		$static.html("").append($btn);

		// Prevent clicks on the cell from activating the grid row
		$cell.on("click", function(e) {
			if ($(e.target).closest(".take-action-btn").length) {
				e.stopPropagation();
				e.stopImmediatePropagation();
			}
		});
	});
}

// Fallback: handles button click when a row is opened in edit/form view
frappe.ui.form.on("Contract Compliance Checker Item", {
	take_action: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];

		if (!row.comment) {
			frappe.msgprint(__("No compliance issue found for this row."));
			return;
		}

		frappe.call({
			method: "one_fm.operations.doctype.contract_compliance_checker.contract_compliance_checker.get_take_action_data",
			args: {
				project: frm.doc.project,
				item: row.item,
				comment: row.comment,
				from_date: row.from_date,
				to_date: row.to_date
			},
			callback: function(r) {
				if (r.message && r.message.path) {
					let url = new URL(r.message.path, window.location.origin);
					let params = r.message.params || {};
					Object.entries(params).forEach(function([key, value]) {
						if (value) url.searchParams.set(key, value);
					});
					window.open(url.toString(), "_blank");
				} else {
					frappe.msgprint(__("Unable to determine the appropriate action for this item."));
				}
			}
		});
	}
});
