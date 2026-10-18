// List pills take a Workflow State's own Style colour instead of a guess from the words.
(function () {
	const STYLE_COLOURS = {
		Success: "green",
		Warning: "orange",
		Danger: "red",
		Primary: "blue",
		Inverse: "black",
		Info: "light-blue",
	};

	function state_colour(value) {
		const style = (frappe.boot.workflow_state_styles || {})[value];
		return STYLE_COLOURS[style];
	}

	const guess_colour = frappe.utils.guess_colour;
	frappe.utils.guess_colour = function (text) {
		return state_colour(text) || guess_colour.apply(this, arguments);
	};

	const get_indicator = frappe.get_indicator;
	frappe.get_indicator = function (doc, doctype, show_workflow_state) {
		const value = doc.workflow_state;
		if (show_workflow_state && value && !frappe.workflow.get_state_fieldname(doctype || doc.doctype)) {
			return [__(value), state_colour(value) || guess_colour(value), `workflow_state,=,${value}`];
		}
		return get_indicator.apply(this, arguments);
	};
})();
