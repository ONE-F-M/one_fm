// Copyright (c) 2023, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Google Sheet Data Export', {
	refresh: (frm) => {
		if(!frm.is_new()){
			frm.add_custom_button(__('Export Sheet'), function(){
				export_data(frm);
			});	
			const doctype = frm.doc.reference_doctype;
			if (doctype) {
				frappe.model.with_doctype(doctype, () => set_filters_and_field(frm));	
			}
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
		let columns = {};
		Object.keys(frm.fields_multicheck).forEach((dt) => {
		const options = frm.fields_multicheck[dt].get_checked_options();
		columns[dt] = options;
		});
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
	link:(frm)=>{
		if(frm.doc.have_existing_sheet == 1){
			let url = frm.doc.link
			let capturedId = url.match(/\/d\/(.+)\//)
			frm.set_value('google_sheet_id', capturedId[1])
		}
	}
});

const can_export = (frm) => {
	const doctype = frm.doc.reference_doctype;
	const parent_multicheck_options = frm.fields_multicheck[doctype]
		? frm.fields_multicheck[doctype].get_checked_options()
		: [];
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
	var client_id = frm.doc.client_id

	if(frm.doc.field_cache == null && frm.doc.filter_cache == null){
		filters = frm.filter_list.get_filters().map((filter) => filter.slice(1, 4))

		let columns = {};
		Object.keys(frm.fields_multicheck).forEach((dt) => {
			const options = frm.fields_multicheck[dt].get_checked_options();
			columns[dt] = options;
		});
		select_columns = JSON.stringify(columns);
	}
	else{
		filters = JSON.parse(frm.doc.filter_cache)
		select_columns = frm.doc.field_cache;
	}
	
		frappe.call({
			method: "one_fm.one_fm.doctype.google_sheet_data_export.exporter.build_connection_with_sheet",
			args: {
				doc:frm.doc
			},
			callback: function(r) {
				if(r.message){
					frappe.call({
						method: "one_fm.one_fm.doctype.google_sheet_data_export.exporter.export_data",
						args: {
							doctype: frm.doc.reference_doctype,
							select_columns: select_columns,
							filters: filters,
							file_type: frm.doc.file_type,
							template: true,
							with_data: 1,
							link: frm.doc.link,
							google_sheet_id: frm.doc.google_sheet_id,
							sheet_name: frm.doc.sheet_name,
							have_existing_sheet: frm.doc.have_existing_sheet,
							owner:frm.doc.owner
						},
						callback: function(r) {
							if(r.message) {
								
								frm.set_value('link', r.message['link'])
								frm.set_value('google_sheet_id', r.message['google_sheet_id'])
								frm.set_value('sheet_name', r.message['sheet_name'])
								}
							}
						});
				}
				else{
					if(frm.doc.link != null && frm.doc.have_existing_sheet == 1){
						frappe.msgprint({
							title: __('Warning'),
							message: __(`We do not have access to this sheet. Kindly, share your sheet with the following:<br><br> <b>${client_id}</b>`),
							indicator: 'orange',
							primary_action:{
								action() {
									frappe.utils.copy_to_clipboard(client_id);
								}
							},
							primary_action_label:`<i class="fa fa-copy"></i>`,
						});
					}
										
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
};

const set_filters_and_field = (frm) => {
	const parent_wrapper = frm.fields_dict.fields_multicheck.$wrapper;
	const filter_wrapper = frm.fields_dict.filter_list.$wrapper;
	const doctype = frm.doc.reference_doctype;
	const related_doctypes = get_doctypes(doctype);

	parent_wrapper.empty();
	filter_wrapper.empty();

	let filters = JSON.parse(frm.doc.filter_cache)
	frm.filter_list = new frappe.ui.FilterGroup({
		parent: filter_wrapper,
		doctype: doctype,
		on_change: () => {},
	});
	filters.forEach((filter) => {
		frm.filter_list.add_filter(doctype, filter[0],filter[1],filter[2])
	})
	
	// Add 'Select All' and 'Unselect All' button
	
	make_multiselect_buttons(parent_wrapper);
	frm.fields_multicheck = {};
	related_doctypes.forEach((dt) => {
		frm.fields_multicheck[dt] = add_doctype_field_multicheck_control(frm, dt, parent_wrapper);
	});

}
const set_field_options = (frm) => {
	const parent_wrapper = frm.fields_dict.fields_multicheck.$wrapper;
	const filter_wrapper = frm.fields_dict.filter_list.$wrapper;
	const doctype = frm.doc.reference_doctype;
	const related_doctypes = get_doctypes(doctype);
	
	parent_wrapper.empty();
	filter_wrapper.empty();

	frm.filter_list = new frappe.ui.FilterGroup({
		parent: filter_wrapper,
		doctype: doctype,
		on_change: () => {},
	});

	// Add 'Select All' and 'Unselect All' button
	make_multiselect_buttons(parent_wrapper);

	frm.fields_multicheck = {};
	related_doctypes.forEach((dt) => {
		frm.fields_multicheck[dt] = add_doctype_field_multicheck_control(frm, dt, parent_wrapper);
	});

	frm.refresh();
};

const make_multiselect_buttons = (parent_wrapper) => {
	const button_container = $(parent_wrapper).append('<div class="flex"></div>').find(".flex");

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

	$(button_container)
		.find(".frappe-control")
		.map((index, button) => {
			$(button).css({ "margin-right": "1em" });
		});

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

const add_doctype_field_multicheck_control = (frm, doctype, parent_wrapper) => {
	const fields = get_fields(doctype);

	var selected_fields = []
	var column;
	if(frm.doc.field_cache !== undefined){
		column = JSON.parse(frm.doc.field_cache)
		let c =[]
		selected_fields = Object.values(column)
		for (let i = 1; i < selected_fields.length; i++) {
			selected_fields[0] = c.concat(selected_fields[0],selected_fields[i])
		}
		selected_fields = selected_fields[0]
	}
	const options = fields.map((df) => {
		let check = 1
		if(!selected_fields.includes(df.fieldname)){
			check = 0
		}
		return {
			label: df.label,
			value: df.fieldname,
			danger: df.reqd,
			checked: check,
		};
		
	});

	const multicheck_control = frappe.ui.form.make_control({
		parent: parent_wrapper,
		df: {
			label: doctype,
			fieldname: doctype + "_fields",
			fieldtype: "MultiCheck",
			options: options,
			columns: 3,
		},
		render_input: true,
	});

	multicheck_control.refresh_input();
	return multicheck_control;
};

const filter_fields = (df) => frappe.model.is_value_type(df) && !df.hidden;
const get_fields = (dt) => frappe.meta.get_docfields(dt).filter(filter_fields);
