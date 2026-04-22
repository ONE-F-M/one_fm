// Copyright (c) 2020, ONE FM and contributors
// For license information, please see license.txt

var values = '';

function open_form(frm, doctype, child_doctype, parentfield) {
	frappe.model.with_doctype(doctype, () => {
    let new_doc = frappe.model.get_new_doc(doctype);
    new_doc.type  = 'Contracts';
		new_doc.amended_from = frm.doc.name;
		new_doc.client = frm.doc.client;
		new_doc.project = frm.doc.project;
		new_doc.price_list = frm.doc.price_list;
		new_doc.workflow_state = '';
		frappe.ui.form.make_quick_entry(doctype, null, null, new_doc);
	});

}
frappe.ui.form.on('Contracts', {
	setup(frm) {
		frm.make_methods = {
			'Sales Invoice': () => {
				open_form(frm, "Sales Invoice", null, null);
			},
			'Delivery Note': () => {
				open_form(frm, "Delivery Note", null, null);
			},
		};
	},
	use_portal_for_invoice:function(frm){
		if(frm.doc.use_portal_for_invoice){
			if(!frm.doc.password_management){
				var d = new frappe.ui.Dialog({
					title: __("Online Portal Credentials"),
					fields: [
						{"fieldname":"url", "fieldtype":"Data", "label":__("URL"),
							"default" : "https://",reqd: 1},
						{"fieldname":"user_name", "fieldtype":"Data", "label":__("User Name"),
							reqd: 1},
						{"fieldname":"password", "fieldtype":"Password", "label":__("Password"),
							reqd: 1},
						{"fieldname":"client", "fieldtype":"Link","options":"Customer", "label":__("Client"),
							"default":frm.doc.client,reqd: 1,hidden:1},
					]
				});
				d.set_primary_action(__("Save"),function(){
					values = d.get_values();
					d.hide();
				})
				d.show()
			}
			else{
				msgprint('Password Management is already exist for this contract');
			}
		}
	},
	before_save:function(frm){
		if(frm.doc.use_portal_for_invoice && !frm.doc.password_management){
			frappe.call({
				method: "one_fm.operations.doctype.contracts.contracts.insert_login_credential",
				args: values,
				callback: function(r) {
					if(!r.exc){
						frm.set_value("password_management",r.message.name);
						frm.refresh_field("password_management");
					}
				}
			});
		}
	},
	validate: function(frm){
		if(!frm.doc.client || !frm.doc.project || !frm.doc.start_date){
			frappe.msgprint({
				title: __('Value Missing Error'),
				indicator: 'red',
				message: __('You have to fill Client, Project and Contract Start Date Before Saving a Contract.')
			});
			validated = false;
		}
		if(frm.doc.end_date){
			if(frm.doc.end_date < frm.doc.start_date){
				frappe.msgprint({
					title: __('Validation Error'),
					indicator: 'red',
					message: __('Contract End Date Cannot be before Contracts Start Date.')
				});
				validated = false;
			}
		}
	},
	start_date: function(frm){
		if(frm.doc.start_date){
			frm.set_value('end_date', frappe.datetime.add_days(frm.doc.start_date, 364))
		}
	},
	before_insert: (frm)=>{
		if(frm.is_new()){
			frm.doc.workflow_state=null;
		}
	},
	refresh:function(frm){
		// create delivery note and reroute to the form in draft mode
		
		if (frm.doc.workflow_state == "Active" && frappe.user_roles.includes("Operations Manager")){

			//  Amend contract
			frm.add_custom_button(__("Create Missing Post Schedules"), function() {
				frappe.call({
						
						method: 'one_fm.operations.doctype.operations_post.operations_post.create_new_schedule_for_project',
						args: {proj:frm.doc.project},
						callback: function(r) {
							if(!r.exc){
								frappe.show_alert({
										message:__('Post Schedules are being created in the background.'),
										indicator:'green'
								}, 5);
								
							}
						},
						
					})
			});

		}
		

		if (frm.doc.workflow_state == "Inactive" && frappe.user_roles.includes("Finance Manager")){

			//  Amend contract
			frm.add_custom_button(__("Amend Contract"), function() {
				open_form(frm, "Contracts", null, null);
			});

		} else if(frm.doc.workflow_state=='Active' && frappe.user_roles.includes("Finance Manager")){
			// create Delivery Note
			frm.add_custom_button(__("Create Delivery Note"), function() {
				create_delivery_note(frm);
			}).addClass('btn btn-danger');

			// Generate Invoice
			frm.add_custom_button(__("Generate Invoice"), function() {
				// Get contract start year and current year
				let contract_start_year = frm.doc.start_date ? new Date(frm.doc.start_date).getFullYear() : new Date().getFullYear();
				let current_year = new Date().getFullYear();
				
				// Generate year options from current year back to contract start year
				let year_options = [];
				for (let year = current_year; year >= contract_start_year; year--) {
					year_options.push({ value: year.toString(), label: year.toString() });
				}
				
				// Month options
				let month_options = [
					{ value: 1, label: __("January") },
					{ value: 2, label: __("February") },
					{ value: 3, label: __("March") },
					{ value: 4, label: __("April") },
					{ value: 5, label: __("May") },
					{ value: 6, label: __("June") },
					{ value: 7, label: __("July") },
					{ value: 8, label: __("August") },
					{ value: 9, label: __("September") },
					{ value: 10, label: __("October") },
					{ value: 11, label: __("November") },
					{ value: 12, label: __("December") },
				];
				
				// Set default to current month and year
				let current_month = (new Date().getMonth() + 1).toString();
				let current_year_str = current_year.toString();
				
				let d = new frappe.ui.Dialog({
					title: __('Select Invoice Period'),
					fields: [
						{
								label: __('Month'),
								fieldname: 'month',
								fieldtype: 'Select',
								options: month_options,
								default: current_month,
								reqd: 1
						},
						{
								label: __('Year'),
								fieldname: 'year',
								fieldtype: 'Select',
								options: year_options,
								default: current_year_str,
								reqd: 1
						}
					],
					primary_action_label: __('Generate'),
					primary_action(values) {						
						frappe.call({
							doc: frm.doc,
							method: 'generate_sales_invoice',
							args: values,
							callback: function(r) {
								if(!r.exc){
									frappe.show_alert({
											message:__('Sales Invoice created successfully'),
											indicator:'green'
									}, 5);
									
									if(r.message && r.message.name) {
										frappe.set_route('Form', 'Sales Invoice', r.message.name);
									} else {
										frappe.msgprint(__('Sales Invoice created successfully'));
										frm.reload_doc();
									}
								}
							},
							freeze: true,
							freeze_message: (__('Creating Sales Invoice'))
						})
						d.hide();
					}
			});

			d.show();
			}).addClass("btn-primary");
		}



		var days,management_fee_percentage,management_fee;
		frm.set_query("bank_account", function() {
			return {
				"filters": {
					"party_type": 'Customer',
					"party": frm.doc.client
				}
			};
		});
		frm.refresh_field("bank_account");
		frm.set_query("project", function() {
			return {
				filters:{
					project_type: 'External',
					customer: frm.doc.client

				}
			};
		});
		frm.refresh_field("project");
		frm.set_query("customer_address", function() {
			return {
				"filters": {
					"link_doctype": 'Customer',
					"link_name": frm.doc.client
				}
			};
		});
		frm.set_query("sales_invoice_print_format", function() {
			return {
				filters: {
					"doc_type": 'Sales Invoice'
				}
			};
		});
		frm.refresh_field("customer_address");
		frm.set_query("price_list", function() {
			return {
				"filters": {
					//"customer": frm.doc.client,
					"selling": 1
				}
			};
		});
		frm.refresh_field("price_list");
		frm.fields_dict['items'].grid.get_field('item_code').get_query = function() {
            return {
                filters:{
					// is_stock_item: 0,
					is_sales_item: 1,
                    disabled: 0
                }
            }
        }
		frm.fields_dict['items'].grid.get_field('item_price').get_query = function(frm, cdt, cdn) {
            let d = locals[cdt][cdn];
            return {
                filters:{
					price_list: cur_frm.doc.price_list,
                    customer: cur_frm.doc.client,
					selling: 1,
                    item_code: d.item_code
                }
            }
        }
        frm.refresh_field("items");

		frm.fields_dict['items'].grid.get_field('site').get_query = function() {
            return {
                filters:{
					project: frm.doc.project
                }
            }
        }
        frm.refresh_field("assets");
		set_hide_management_fee_fields(frm);
		frm.events.open_sections_onload(frm);
		
		frm.fields_dict['contract_items_operation'].grid.get_field('item_code').get_query = function() {
			let valid_items = frm.doc.items.map(item => item.item_code);
			return {
				filters: [
					['Item', 'item_code', 'in', valid_items]
				]
			};
		};

		// Role-based read-only enforcement.
		// Uses frm.meta.fields (ordered by idx from DB) to walk sections reliably.
		// Wrapped in setTimeout to guarantee the form DOM is fully rendered.
		setTimeout(() => {
			const user_roles = frappe.user_roles;
			const is_system_manager = user_roles.includes('System Manager');
			const is_legal = user_roles.includes('Legal Manager') || user_roles.includes('Legal User');
			// Fires when Legal Manager is NOT in their designated editing state.
			// In 'Submit to Legal Manager' they edit the full section normally.
			// In all other states they should only see the 2 notification fields.
			const is_active_legal = is_legal && !frm.is_new() && frm.doc.workflow_state !== 'Submit to Legal Manager';

			// Frappe locks the entire form at the perm level when the workflow
			// state's allow_edit role doesn't match the current user. We override
			// that lock for Legal Manager / Legal User on Active contracts so they
			// can edit the two notification fields. Everything else is locked via
			// the section_role_map below.
			if (is_active_legal) {
				frm.perm[0] = Object.assign({}, frm.perm[0], { write: 1 });
				frm.enable_save();
				// Hide the "not editable due to Workflow" banner
				frm.$wrapper.find('.form-message.yellow').hide();
			}

			// Optional: log roles to browser console for debugging
			console.log('[Contracts] user_roles:', user_roles);

			if (is_system_manager) {
				console.log('[Contracts] System Manager — skipping role enforcement');
				return;
			}

			// Map section-break fieldname → role(s) that may EDIT that section.
			// [] = read-only to everyone; omit entry = leave as-is (custom sections)
			const section_role_map = {
				'__header__':                       ['Sales Manager'],
				'section_break_8':                  ['Sales Manager'],
				'section_break_20':                 ['Legal Manager'],
				'section_break_26':                 ['Finance Manager'],
				'section_break_35':                 ['Finance Manager'],
				'operational_requirements_section': ['Operation Admin'],
				'section_break_55':                 [],
			};

			// Fieldtypes that must never be set read_only (they control layout)
			const layout_types = new Set(['Section Break', 'Column Break', 'Tab Break', 'HTML', 'Heading']);
			const skip_fields  = new Set([
				'amended_from', 'password_management', 'workflow_state',
				// These dates are always auto-calculated — never allow manual edits
				'contract_end_internal_notification_date',
				'contract_termination_decision_period_date',
			]);

			let current_section = '__header__';
			let processed = 0;

			// frm.meta.fields is ordered by DB idx — the definitive rendering order
			(frm.meta.fields || []).forEach(df => {
				const fn = df.fieldname;
				const ft = df.fieldtype;

				// Advance current section when we hit a Section Break
				if (ft === 'Section Break') {
					current_section = section_role_map.hasOwnProperty(fn) ? fn : '__unknown__';
					return; // never touch section break fields themselves
				}


				// Skip layout and system fields
				if (layout_types.has(ft) || skip_fields.has(fn)) return;

				const owners = section_role_map[current_section];
				if (owners === undefined) return; // unknown/custom section → leave alone

				const can_edit = owners.length > 0 && owners.some(r => user_roles.includes(r));
				frm.set_df_property(fn, 'read_only', can_edit ? 0 : 1);
				processed++;
			});

			console.log(`[Contracts] Role enforcement applied to ${processed} fields. Section: ${current_section}`);
			frm.refresh_fields();

			// --- Legal Manager / Legal User special override ---
			// Outside of 'Submit to Legal Manager' state: lock the rest of the
			// Legal & Compliance section and only unlock the 2 notification fields.
			if (is_active_legal) {
				// Extra fields in section_break_20 that should stay read-only
				['contract', 'is_auto_renewal', 'contract_date'].forEach(
					fn => frm.set_df_property(fn, 'read_only', 1)
				);
				// These two are always editable for Legal Manager
				const legal_editable = [
					'contract_end_internal_notification',
					'contract_termination_decision_period'
				];
				legal_editable.forEach(fn => frm.set_df_property(fn, 'read_only', 0));
				frm.refresh_fields();
				console.log('[Contracts] Legal Manager override: only notification fields unlocked.');
			}
			// --- end Legal Manager override ---

			
				const ops_grid = frm.get_field('contract_items_operation');
				if (ops_grid && ops_grid.grid) {
					ops_grid.grid.cannot_add_rows = true;
					ops_grid.grid.cannot_delete_rows = true;
					
					if (user_roles.includes('Operation Admin')) {
						['item_code', 'count', 'rate_type', 'uom'].forEach(fieldname => {
							ops_grid.grid.update_docfield_property(fieldname, 'read_only', 1);
						});
					}

					ops_grid.grid.refresh();
				}
			
		}, 300);

	},
	customer_address:function(frm){
		if(frm.doc.customer_address){
			erpnext.utils.get_address_display(frm, 'customer_address', 'address_display')
		}
	},
	bank_account:function(frm){
		if(frm.doc.bank_account){
			frappe.call({
				method: 'frappe.client.get_value',
				args:{
					'doctype':'Bank Account',
					'filters':{
						'name': frm.doc.bank_account
					},
					'fieldname':[
						'bank',
						'iban'
					]
				},
				callback:function(s){
					if (!s.exc) {
						frm.set_value("bank_name",s.message.bank);
						frm.set_value("iban",s.message.iban);
						frm.refresh_field("bank_name");
						frm.refresh_field("iban");
					}
				}
			});
		}
	},
	create_sales_invoice_as: function(frm){
		set_hide_management_fee_fields(frm);
	},
	open_sections_onload(frm) {
		// run after layout is ready
        frappe.after_ajax(() => {
            let keep_closed = ['section_break_15', 'section_break_36', 'section_break_55', 'sales_invoice_print_settings_section'];
			frm.layout.sections.forEach(sec => {
                if (sec.df && sec.df.collapsible) {
					if (!keep_closed.includes(sec.df.fieldname)) {
                        sec.collapse(false);
                    }
                }
            });
        });
	}
});

var set_hide_management_fee_fields = function(frm) {
	var management_fee_percentage = frappe.meta.get_docfield("Contract Item", "management_fee_percentage", frm.doc.name);
	var management_fee = frappe.meta.get_docfield("Contract Item", "management_fee", frm.doc.name);

	// Guard: fields may not exist if Contract Item was restructured
	if (!management_fee_percentage || !management_fee) return;

	if(frm.doc.create_sales_invoice_as == 'Invoice for Airport'){
		management_fee_percentage.hidden = 0;
		management_fee.hidden = 0;
	}
	else{
		management_fee_percentage.hidden = 1;
		management_fee.hidden = 1;
	}
	frm.refresh_field("items");
};

frappe.ui.form.on('POC', {
	form_render: function(frm, cdt, cdn) {
		let doc = locals[cdt][cdn];
		if(doc.poc !== undefined){
			get_contact(doc);
		}
	},
	poc: function(frm, cdt, cdn){
		let doc = locals[cdt][cdn];
		if(doc.poc !== undefined){
			get_contact(doc);
		}
	}
});

function get_contact(doc){
	let operations_site_poc = doc.poc;
	frappe.call({
		method: 'frappe.client.get',
		args: {
			doctype: 'Contact',
			name: operations_site_poc
		},
		callback: function(r) {
			if(!r.exc) {
				set_contact(r.message);
			}
		}
	});
}

function set_contact(doc){
	let {email_ids, phone_nos} = doc;
	console.log(email_ids, phone_nos);
	let contact_details = ``;
	for(let i=0; i<email_ids.length;i++){
		contact_details += `<p>Email: ${email_ids[i].email_id}</p>\n`;
	}

	for(let j=0; j<phone_nos.length;j++){
		contact_details += `<p>Phone: ${phone_nos[j].phone}</p>\n`;
	}
	console.log(contact_details);
	$('div[data-fieldname="contact_html"]').empty().append(`<div class="address-box">${contact_details}</div>`);
}

frappe.ui.form.on('Contract Item', {
	item_code: function(frm, cdt, cdn) {
		let d = locals[cdt][cdn];
		if(d.item_code){
			frappe.model.set_value(d.doctype, d.name, "item_price", null);
			frappe.model.set_value(d.doctype, d.name, "price_list_rate", 0);
			frappe.model.set_value(d.doctype, d.name, "rate", 0);
			frappe.model.set_value(d.doctype, d.name, "gender", null);
			frappe.model.set_value(d.doctype, d.name, "working_days", null);
			frappe.model.set_value(d.doctype, d.name, "working_hours", null);

			// Fetch variant attributes (Gender, Working Days, Working Hours)
			frappe.call({
				method: "one_fm.operations.doctype.contracts.contracts.get_item_variant_attributes",
				args: { item_code: d.item_code },
				callback: function(r) {
					if (!r.exc && r.message) {
						frappe.model.set_value(d.doctype, d.name, "gender", r.message.gender);
						frappe.model.set_value(d.doctype, d.name, "working_days", r.message.working_days);
						frappe.model.set_value(d.doctype, d.name, "working_hours", r.message.working_hours);
					} else {
						frappe.model.set_value(d.doctype, d.name, "gender", null);
						frappe.model.set_value(d.doctype, d.name, "working_days", null);
						frappe.model.set_value(d.doctype, d.name, "working_hours", null);
					}
				}
			});
		} else {
			// Clear fields if item_code is cleared
			frappe.model.set_value(d.doctype, d.name, "gender", null);
			frappe.model.set_value(d.doctype, d.name, "working_days", null);
			frappe.model.set_value(d.doctype, d.name, "working_hours", null);
		}
		set_item_price(frm, d);
	},
	rate_type: function(frm, cdt, cdn) {
		let child = locals[cdt][cdn];
		set_item_price(frm, child);
	},
	management_fee_percentage: function(frm, cdt, cdn){
		let d = locals[cdt][cdn];
		let management_fee = d.price_list_rate * (flt(d.management_fee_percentage / 100))
		frappe.model.set_value(d.doctype, d.name, "management_fee", management_fee);
		frappe.model.set_value(d.doctype, d.name, "rate", d.price_list_rate + management_fee);
		frm.refresh_field("items");
	}
});

var set_item_price = function(frm, row) {
	if(row.item_code && row.rate_type){
		frappe.call({
			method: 'frappe.client.get',
			args:{
				'doctype':'Item Price',
				'filters':{
					'item_code': row.item_code,
					'price_list': frm.doc.price_list,
					'customer': frm.doc.client,
					'uom': row.rate_type,
					'selling': 1
				}
			},
			callback:function(r){
				if(r.message){
					frappe.model.set_value(row.doctype, row.name, "item_price", r.message.name);
					frappe.model.set_value(row.doctype, row.name, "price_list_rate", r.message.price_list_rate);
					frappe.model.set_value(row.doctype, row.name, "rate", r.message.price_list_rate);
				}
				else{
					frappe.model.set_value(row.doctype, row.name, "item_price", '');
					frappe.model.set_value(row.doctype, row.name, "price_list_rate", 0);
					frappe.model.set_value(row.doctype, row.name, "rate", 0);
					frappe.msgprint("Rate not found for item" + row.item_code)
				}
				frm.refresh_field("items");
			}
		});
	}
};

frappe.ui.form.on('Contract Addendum', {
	end_date: function(frm, cdt, cdn) {
		let doc = locals[cdt][cdn];
	},
	addendums_add: function(frm, cdt, cdn){
		let doc = locals[cdt][cdn];
		if(doc.idx == 1){
			frappe.model.set_value(doc.doctype, doc.name, "version", "1.0");
		}else{

		}
	}
})

// create delivery note
let create_delivery_note = frm => {
	if(frm.doc.create_sales_invoice_as=="Single Invoice"){
		// Create general delivery note on single invoice

			let table_fields = dn_table_field(frm);

			const dialog = new frappe.ui.Dialog({
					title: __('Create Delivery Note'),
					static: false,
					fields: dn_fields(frm, table_fields),
					primary_action: async function(values) {
						// validate values
						validate_dn_rows(frm, values);
						// // process
						process_delivery_note(frm, values);

						dialog.hide();
					},
					primary_action_label: __('Submit')
				});
				dialog.show();
				// initialize dialog table
				update_dn_table(frm, dialog);



	} else if(frm.doc.create_sales_invoice_as=="Separate Item Line for Each Site" ||
		frm.doc.create_sales_invoice_as=="Separate Invoice for Each Site"){
		frm.call('get_contract_sites').then(res=>{
			if(res.message.length>0){
				let sites = res.message;
				// create dialog
				let table_fields = dn_table_field(frm);
				table_fields.push({
					fieldname: "site", fieldtype: "Link",
					in_list_view: 1, label: "Site", reqd:1,

				})

				const dialog = new frappe.ui.Dialog({
						title: __('Create Delivery Note'),
						static: false,
						fields: dn_fields(frm, table_fields),
						primary_action: async function(values) {
							// validate values
							validate_dn_rows(frm, values);
							// // process
							// process delivery note for item line per site
							process_delivery_note(frm, values);

							dialog.hide();
						},
						primary_action_label: __('Submit')
				});
				dialog.show();
				// end create dialog
				sites.forEach((site, i) => {
					frm.doc.items.forEach((item, i) => {
						if(item.subitem_group!='Service'){
							dialog.fields_dict.items.df.data.push(
								{
									item_code: item.item_code, qty: item.count,
									rate: item.rate, site: site}
							);
						}
					});
				});
				dialog.fields_dict.items.grid.refresh();
			}
		})
	} else if(false){

	}
}


let dn_table_field = frm => {
	// delivery note items table
	return [
			{
				fieldname: "item_code", fieldtype: "Link",
				in_list_view: 1, label: "Item",
				options: "Item", reqd: 1,
				get_query: () => {
					return {
						filters: {
							'subitem_group': ['!=', 'Service']
						}
					}
				}
			},
			{
				fieldname: "qty", fieldtype: "Int",
				in_list_view: 1, label: "QTY", reqd:1,
				default: 1
			},
			{
				fieldname: "rate", fieldtype: "Currency",
				in_list_view: 1, label: "Rate", reqd:1,
				default: 1
			}

		];
}

let dn_fields = (frm, table_fields) => {
	// return dialog fields
	return [
		{
			fieldname: "items",
			fieldtype: "Table",
			label: "Items",
			cannot_add_rows: false,
			cannot_delete_rows: false,
			in_place_edit: true,
			reqd: 1,
			data: [],
			fields: table_fields
		}
	]
}

let validate_dn_rows = (frm, values) => {
	// validate delivery note rows if empty
	values.items.forEach((item, i) => {
		if(!item.item_code || !item.qty){
			frappe.throw(`Please select option for
				<b>${item.idx}</b>`)
		}
	});
}


let update_dn_table = (frm, dialog) => {
	// auto file delivery note table fields
	frm.doc.items.forEach((item, i) => {
		if(item.subitem_group!='Service'){
			dialog.fields_dict.items.df.data.push(
				{ item_code: item.item_code, qty: item.count, rate: item.rate}
			);
		}
	});
	dialog.fields_dict.items.grid.refresh();
}


// process filter
let process_delivery_note = (frm, values)=>{
	// set items sorting and filtering
	frappe.call({
		doc: frm.doc,
		args: {dn_items:values},
		method: 'make_delivery_note',
		callback: function(r) {
			if(!r.exc){
				if(r.message){
					frappe.show_alert({
					    message:__('Delivery Note created successfully'),
					    indicator:'green'
					}, 5);
					frappe.msgprint(__('Delivery Note created successfully'))
					// reload_doc
					frm.reload_doc();
					frappe.set_route('List', 'Delivery Note', {
						contracts: frm.doc.name
					})
				}
			}
		},
		freeze: true,
		freeze_message: (__('Creating Delivery Note'))
	});
}
