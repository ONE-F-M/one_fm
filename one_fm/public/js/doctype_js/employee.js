frappe.ui.form.on('Employee', {
	refresh: function(frm) {
		hideFields(frm);
		frm.trigger('set_queries');
		set_mandatory(frm);
        set_shift_working_btn(frm);
        filterDefaultShift(frm);
        setProjects(frm);
	},
	status: function(frm){
		set_mandatory(frm);
	},
    shift_working: function(frm) {
        set_shift_working_btn(frm);
        filterDefaultShift(frm);
        setProjects(frm);
        TransferToNonShift(frm);
    },
	set_queries: frm => {
		// set bank account query
		frm.set_query('bank_account', function() {
			return {
				filters: {
					"party_type": frm.doc.doctype,
					"party": frm.doc.name
				}
			};
		});
	}
});


frappe.ui.form.on('Employee Incentive', {
	refresh: function(frm) {
		frm.trigger('set_queries');
	},
	set_queries: frm => {
		// set leave policy query
		frm.set_query('leave_policy', function() {
			return {
				filters: {
					"docstatus": 1
				}
			};
		});
	}
});

// SET MANDATORY FIELDS
let set_mandatory = frm => {
	if (['Left', 'Court Case', 'Absconding', 'Vacation'].includes(frm.doc.status)){
		toggle_required(frm, 0);
	} else {
		toggle_required(frm, 1);
	}
}

// TOGGLE REQUIRED
let toggle_required = (frm, state) => {
	['leave_policy', 'permanent_address', 'cell_number',
	'last_name_in_arabic'].forEach((item, i) => {
		frm.toggle_reqd(item, state);
	});
}


// Hide un-needed fields
const hideFields = frm => {
    $("[data-doctype='Employee Checkin']").hide();
}

var set_shift_working_btn = function(frm) {
	yes_no_html_buttons(frm, frm.doc.shift_working, 'shift_working_html', 'shift_working', 'Will The Employee Work In Shifts?');
};

var yes_no_html_buttons = function(frm, val, html_field, field_name, label) {
	var $wrapper = frm.fields_dict[html_field].$wrapper;
	var selected = 'btn-primary';
	var field_btn_html = field_name+'_btn_html';
	var field_html = `<div><label class="control-label" style="padding-right: 0px;">${label}</label></div><div>
		<button class="btn btn-default btn-xs ${val ? selected: ''} ${field_btn_html}" type="button" data='Yes'>Yes</button>
		<button class="btn btn-default btn-xs ${!val ? selected: ''} ${field_btn_html}" type="button" data='No'>No</button>
	</div>`;
	$wrapper
		.html(field_html);
	$wrapper.on('click', '.'+field_btn_html, function() {
		if(frm.doc.docstatus == 0){
			var $btn = $(this);
			$wrapper.find('.'+field_btn_html).removeClass('btn-primary');
			$btn.addClass('btn-primary');
			if(field_name == 'open_to_different'){
				frm.set_value(field_name, $btn.attr('data'));
			}
			else{
				frm.set_value(field_name, $btn.attr('data')=='Yes'? true:false);
			}
		}
	});
};


const filterDefaultShift = (frm) => {
    let state = 0;
    if (frm.doc.shift_working==1) {
        state=1;
    }
    frm.set_query('default_shift', () => {
        return {
            filters: {
                shift_work: state
            }
        }
    })
}

const setProjects = frm => {

}


const TransferToNonShift = frm => {
        frm.set_value({
            'project': '',
            'shift': '',
            'site': '',
            'holiday_list': '',
        })
}

frappe.ui.form.on('Employee', {
    onload: function(frm) {
        var designation = frm.doc.designation;
        if (designation == "General Manager") {
            frm.set_df_property("reports_to", "reqd", 1);
        } else {
            frm.set_df_property("reports_to", "reqd", 0);
        }
    }
});