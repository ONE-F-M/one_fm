
frappe.provide('enhancements');

frappe.ui.form.on('Workflow', {
	'refresh': function(frm){
		enhancements.set_docfields();
		// for (var i = frm.doc.transitions.length - 1; i >= 0; i--) {
		// 	cpfa.set_required_fields('refresh',frm.doc.transitions[i]);
		// }
	},
	'document_type': function(frm){
		enhancements.set_docfields();
	},
})

frappe.ui.form.on('Workflow Transition', {
	'allowed': function(doc, cdt, cdn){
		if (locals[cdt][cdn].allowed){
			//cpfa.set_required_fields('allowed',locals[cdt][cdn]);
		}
	},
	'allowed_user': function(frm, cdt, cdn){
		if (locals[cdt][cdn].allowed_user){
			//cpfa.set_required_fields('allowed_user',locals[cdt][cdn]);
		}
	},
	'allowed_user_field': function(frm, cdt, cdn){
		if (locals[cdt][cdn].allowed_user_field){
			//cpfa.set_required_fields('allowed_user_field',locals[cdt][cdn]);
		}
	},
})


cur_frm.set_query("allowed_user", "transitions", function(frm,dt,dn) {
	var doc = locals[dt][dn];
	return{
		filters: [["Has Role","role","=", doc.allowed]],
		query: "one_fm.overrides.workflow.user_query"
	}
});

enhancements.set_required_fields = function(event, doc){
	if (event == 'refresh'){
		if (doc.allowed){
			event = 'allowed'
		} else if (doc.allowed_user || doc.allowed_user_field){
			event = 'allowed_user'
		}
	}
	if (field == 'allowed'){
		frappe.model.set_value(cdt, cdn, 'allowed_user', '');
		frappe.model.set_value(cdt, cdn, 'allowed_user_field', '');
		frm.set_df_property('allowed_user','reqd',0,frm.doc.name,'transitions');
		frm.set_df_property('allowed_user_field','reqd',0,frm.doc.name,'transitions');
	} else {
		frappe.model.set_value(cdt, cdn, 'allowed', '');
		frm.set_df_property('allowed','reqd',0,frm.doc.name,'transitions');
	}
	
	frm.fields_dict['transitions'].grid.refresh();
}

enhancements.set_docfields = function(){
	var doctype = locals[cur_frm.doctype][cur_frm.docname].document_type
	console.log(doctype)
	if (!doctype) return false;
	
	frappe.call({
		method: 'one_fm.overrides.workflow.get_docfields',
		args: {'doctype': doctype},
		callback: function(r){
			if (r.message){
				var fields_=[]
				console.log(r.message)
				for(var i of r.message){
					fields_.push(i.value) || ""
				}
				cur_frm.fields_dict.transitions.grid.update_docfield_property('allowed_user_field','options',fields_.concat('\n'))
			}
		}
	})
}
