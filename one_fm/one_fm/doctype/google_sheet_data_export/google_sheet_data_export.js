// Copyright (c) 2023, ONE FM and contributors
// For license information, please see license.txt

// Standard (metadata) columns that every DocType has but that are not DocFields,
// so they never show up in frappe.meta.get_docfields(). Offered for the parent
// Document Type only.
const METADATA_FIELDS = [
	{ fieldname: "owner", label: __("Created By"), fieldtype: "Link", options: "User" },
	{ fieldname: "creation", label: __("Created On"), fieldtype: "Datetime" },
	{ fieldname: "modified", label: __("Last Modified On"), fieldtype: "Datetime" },
	{ fieldname: "modified_by", label: __("Last Modified By"), fieldtype: "Link", options: "User" },
	{ fieldname: "docstatus", label: __("Document Status"), fieldtype: "Int" },
	{ fieldname: "idx", label: __("Index"), fieldtype: "Int" },
];

const METADATA_FIELDNAMES = METADATA_FIELDS.map((df) => df.fieldname);

frappe.ui.form.on('Google Sheet Data Export', {
	refresh: (frm) => {
		if(!frm.is_new()){
			const is_system_manager = frappe.user_roles.includes('System Manager');
			const is_in_export_access = frm.doc.export_access && 
				frm.doc.export_access.some(row => row.user === frappe.session.user);
			
			if (is_system_manager || is_in_export_access) {
				frm.add_custom_button(__('Export Sheet'), function(){
					export_data(frm);
				});
			}

			const doctype = frm.doc.reference_doctype;
			if (doctype) {
				frappe.model.with_doctype(doctype, () => set_filters_and_field(frm));
			}
		}
		if(frm.doc.reference_doctype == null){
			// Clear the field and filter
			frm.fields_dict.fields_multicheck.$wrapper.empty();
			frm.fields_dict.filter_list.$wrapper.empty();

		}
	},
	onload: (frm) => {
		frm.set_query("reference_doctype", () => {
			return {
				filters: {
					issingle: 0,
					istable: 0,
					name: ["in", frappe.boot.user.can_export],
				},
			};
		});
	},
	before_save:(frm)=>{
		// Check if exportable
		can_export(frm);

		//save filter and fields
		let columns = collect_selected_columns(frm);
		let filters = frm.filter_list.get_filters().map((filter) => filter.slice(1, 4))

		frm.set_value('filter_cache',  JSON.stringify(filters) )
		frm.set_value('field_cache',  JSON.stringify(columns))
		frappe.call({
			method: "one_fm.one_fm.doctype.google_sheet_data_export.exporter.get_client_id",
			callback: function(r) {
				if(r.message && frm.doc.client_id == null){
					frm.set_value('client_id',  r.message )
				}
			}
		});
	},

	reference_doctype: (frm) => {
		const doctype = frm.doc.reference_doctype;
		if (doctype) {
			frappe.model.with_doctype(doctype, () => set_field_options(frm));
		} else {
			reset_filter_and_field(frm);
		}
	},
	include_hidden_fields: (frm) => {
		redraw_field_options(frm, __("hidden"), (df) => df.hidden);
	},
	include_metadata_fields: (frm) => {
		redraw_field_options(frm, __("metadata"), (df) => METADATA_FIELDNAMES.includes(df.fieldname));
	},
	link:(frm)=>{
		if(frm.doc.have_existing_sheet == 1){
			let url = frm.doc.link
			let capturedId = url.match(/\/d\/(.+)\//)
			frm.set_value('google_sheet_id', capturedId[1])
		}
	}
});

// Re-render the field picker after a visibility toggle, carrying the live
// selection over so that the user does not lose what they have already checked.
// Fields that the toggle just took off the list are dropped from the selection
// and the removal is reported, so that no column silently disappears from the sheet.
const redraw_field_options = (frm, label, is_affected) => {
	const doctype = frm.doc.reference_doctype;
	if (!doctype) return;

	const selection = get_live_selection(frm);
	frappe.model.with_doctype(doctype, () => {
		const removed = prune_selection(frm, selection, is_affected);
		render_field_picker(frm, selection);
		if (removed) {
			frappe.show_alert({
				message: __("{0} selected {1} field(s) removed from the export", [removed, label]),
				indicator: "orange",
			});
		}
	});
};

// Drop selected fields that are no longer offered, and report how many went.
const prune_selection = (frm, selection, is_affected) => {
	let removed = 0;
	Object.keys(selection).forEach((dt) => {
		const available = get_available_fieldnames(frm, dt);
		const kept = selection[dt].filter((fieldname) => {
			if (available.includes(fieldname)) return true;
			const df = frappe.meta.get_docfield(dt, fieldname) || { fieldname: fieldname };
			if (is_affected(df)) removed++;
			return false;
		});
		selection[dt] = kept;
	});
	return removed;
};

const get_available_fieldnames = (frm, dt) => {
	const fieldnames = get_fields(frm, dt).map((df) => df.fieldname);
	if (dt === frm.doc.reference_doctype && frm.doc.include_metadata_fields) {
		fieldnames.push(...METADATA_FIELDNAMES);
	}
	return fieldnames;
};

// Currently checked options, falling back to the saved cache on first render.
const get_live_selection = (frm) => {
	const selection = {};
	if (frm.fields_multicheck && Object.keys(frm.fields_multicheck).length) {
		Object.keys(frm.fields_multicheck).forEach((dt) => {
			selection[dt] = frm.fields_multicheck[dt].get_checked_options();
		});
		const doctype = frm.doc.reference_doctype;
		if (frm.metadata_multicheck) {
			selection[doctype] = (selection[doctype] || []).concat(
				frm.metadata_multicheck.get_checked_options()
			);
		}
		return selection;
	}
	return get_cached_selection(frm);
};

const get_cached_selection = (frm) => {
	if (!frm.doc.field_cache) return {};
	try {
		return JSON.parse(frm.doc.field_cache) || {};
	} catch (e) {
		return {};
	}
};

// Regular fields first, metadata columns last, so that the metadata lands on the
// right hand edge of the sheet (server side column order follows this order).
const collect_selected_columns = (frm) => {
	const columns = {};
	Object.keys(frm.fields_multicheck || {}).forEach((dt) => {
		columns[dt] = frm.fields_multicheck[dt].get_checked_options();
	});
	if (frm.metadata_multicheck) {
		const doctype = frm.doc.reference_doctype;
		columns[doctype] = (columns[doctype] || []).concat(
			frm.metadata_multicheck.get_checked_options()
		);
	}
	return columns;
};

const can_export = (frm) => {
	const doctype = frm.doc.reference_doctype;
	const parent_multicheck_options = collect_selected_columns(frm)[doctype] || [];
	let is_valid_form = false;
	if (!doctype) {
		frappe.msgprint(__("Please select the Document Type."));
	} else if (!parent_multicheck_options.length) {
		frappe.msgprint(__("Atleast one field of Parent Document Type is mandatory"));
	} else {
		is_valid_form = true;
	}
	return is_valid_form;
};

const export_data = (frm) => {
	var select_columns, filters;

	if(frm.doc.field_cache == null && frm.doc.filter_cache == null){
		filters = frm.filter_list.get_filters().map((filter) => filter.slice(1, 4))

		select_columns = JSON.stringify(collect_selected_columns(frm));
	}
	else{
		filters = JSON.parse(frm.doc.filter_cache)
		select_columns = frm.doc.field_cache;
	}

	frappe.call({
		method: "one_fm.one_fm.doctype.google_sheet_data_export.exporter.export_data",
		args: {
			doctype: frm.doc.reference_doctype,
			select_columns: select_columns,
			filters: filters,
			with_data: 1,
			link: frm.doc.link,
			google_sheet_id: frm.doc.google_sheet_id,
			sheet_name: frm.doc.sheet_name,
			owner:frm.doc.owner,
			client_id: frm.doc.client_id,
			name: frm.doc.name,
			include_hidden: frm.doc.include_hidden_fields ? 1 : 0
		},
		freeze: true,
		freeze_message: __("Exporting Data to the Sheet"),
		callback: function(r) {
			if(r.message) {
				frm.set_value('link', r.message['link'])
				frm.set_value('google_sheet_id', r.message['google_sheet_id'])
				frm.set_value('sheet_name', r.message['sheet_name'])
				frappe.msgprint({
					message: __("The Data has been submitted successfully"),
					title: __("Success"),
					indicator: "green"
					});
				}
			}
		});
};

const reset_filter_and_field = (frm) => {
	const parent_wrapper = frm.fields_dict.fields_multicheck.$wrapper;
	const filter_wrapper = frm.fields_dict.filter_list.$wrapper;
	parent_wrapper.empty();
	filter_wrapper.empty();
	frm.filter_list = [];
	frm.fields_multicheck = {};
	frm.metadata_multicheck = null;
};

const set_filters_and_field = (frm) => {
	const filter_wrapper = frm.fields_dict.filter_list.$wrapper;
	const doctype = frm.doc.reference_doctype;

	filter_wrapper.empty();

	let filters = [];
	if (frm.doc.filter_cache) {
		try {
			filters = JSON.parse(frm.doc.filter_cache) || [];
		} catch (e) {
			filters = [];
		}
	}
	frm.filter_list = new frappe.ui.FilterGroup({
		parent: filter_wrapper,
		doctype: doctype,
		on_change: () => {},
	});
	filters.forEach((filter) => {
		frm.filter_list.add_filter(doctype, filter[0],filter[1],filter[2])
	})

	render_field_picker(frm, get_cached_selection(frm));
}
const set_field_options = (frm) => {
	const filter_wrapper = frm.fields_dict.filter_list.$wrapper;
	const doctype = frm.doc.reference_doctype;

	filter_wrapper.empty();

	frm.filter_list = new frappe.ui.FilterGroup({
		parent: filter_wrapper,
		doctype: doctype,
		on_change: () => {},
	});

	render_field_picker(frm, {});

	frm.refresh();
};

// Build one multicheck block per related Document Type, plus a separate
// "Metadata" block for the parent Document Type when metadata is switched on.
const render_field_picker = (frm, selection) => {
	const parent_wrapper = frm.fields_dict.fields_multicheck.$wrapper;
	const doctype = frm.doc.reference_doctype;
	const related_doctypes = get_doctypes(doctype);

	parent_wrapper.empty();
	// breathing room under the last block of checkboxes
	parent_wrapper.addClass("pb-4");

	// Add 'Select All' and 'Unselect All' button
	make_multiselect_buttons(parent_wrapper);

	frm.fields_multicheck = {};
	related_doctypes.forEach((dt) => {
		frm.fields_multicheck[dt] = add_doctype_field_multicheck_control(
			frm, dt, parent_wrapper, selection
		);
	});

	frm.metadata_multicheck = frm.doc.include_metadata_fields
		? add_metadata_multicheck_control(frm, parent_wrapper, selection)
		: null;
};

const make_multiselect_buttons = (parent_wrapper) => {
	const button_container = $(parent_wrapper).append('<div class="flex mb-3"></div>').find(".flex");

	["Select All", "Unselect All"].map((d) => {
		frappe.ui.form.make_control({
			parent: $(button_container),
			df: {
				label: __(d),
				fieldname: frappe.scrub(d),
				fieldtype: "Button",
				click: () => {
					checkbox_toggle(d !== "Select All");
				},
			},
			render_input: true,
		});
	});

	$(button_container).find(".frappe-control").addClass("mr-3");

	function checkbox_toggle(checked) {
		$(parent_wrapper)
			.find('[data-fieldtype="MultiCheck"]')
			.map((index, element) => {
				$(element).find(`:checkbox`).prop("checked", checked).trigger("click");
			});
	}
};

const get_doctypes = (parentdt) => {
	return [parentdt].concat(frappe.meta.get_table_fields(parentdt).map((df) => df.options));
};

const add_doctype_field_multicheck_control = (frm, doctype, parent_wrapper, selection) => {
	const fields = get_fields(frm, doctype);
	const selected_fields = selection[doctype] || [];

	const options = fields.map((df) => {
		return {
			label: df.hidden ? `${df.label} ${hidden_tag()}` : df.label,
			value: df.fieldname,
			danger: df.reqd,
			checked: selected_fields.includes(df.fieldname) ? 1 : 0,
			description: df.hidden ? __("Hidden on the form") : "",
		};
	});

	return make_multicheck(parent_wrapper, doctype, doctype + "_fields", options);
};

const add_metadata_multicheck_control = (frm, parent_wrapper, selection) => {
	const doctype = frm.doc.reference_doctype;
	const selected_fields = selection[doctype] || [];

	const options = METADATA_FIELDS.map((df) => {
		return {
			label: df.label,
			value: df.fieldname,
			checked: selected_fields.includes(df.fieldname) ? 1 : 0,
			description: __("Standard field maintained by the system"),
		};
	});

	return make_multicheck(parent_wrapper, __("{0} · Metadata", [doctype]), "metadata_fields", options);
};

const make_multicheck = (parent_wrapper, label, fieldname, options) => {
	const multicheck_control = frappe.ui.form.make_control({
		parent: parent_wrapper,
		df: {
			label: label,
			fieldname: fieldname,
			fieldtype: "MultiCheck",
			options: options,
			columns: 3,
		},
		render_input: true,
	});

	multicheck_control.refresh_input();
	return multicheck_control;
};

const hidden_tag = () => `<span class="text-muted small">${__("Hidden")}</span>`;

// Fields the current user is allowed to read. Hidden fields are only offered
// when the export is explicitly configured to include them.
// Permlevel access of a child table field is governed by the parent Document Type,
// child tables carry no role permissions of their own.
const filter_fields = (frm, dt, df) => {
	if (!frappe.model.is_value_type(df)) return false;
	if (df.is_virtual) return false;
	if (df.hidden && !frm.doc.include_hidden_fields) return false;
	if (!df.permlevel) return true;
	return frappe.perm.has_perm(frm.doc.reference_doctype, df.permlevel, "read");
};

const get_fields = (frm, dt) =>
	(frappe.meta.get_docfields(dt) || []).filter((df) => filter_fields(frm, dt, df));
