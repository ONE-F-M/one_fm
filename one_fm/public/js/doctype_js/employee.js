frappe.ui.form.on('Employee', {
	refresh: function(frm) {
		hideFields(frm);
		
		set_grd_fields(frm)
		frm.trigger('set_queries');
		set_mandatory(frm);
        set_shift_working_btn(frm);
        filterDefaultShift(frm);
        setProjects(frm);
		if(frappe.user.has_role('HR Manager') && !frm.doc.employee_id){
			frm.add_custom_button(__('Run Employee ID Generation Method'), function() {
				frappe.call({
					doc: frm.doc,
					method: 'run_employee_id_generation',
					callback: function(r) {
						if(!r.exc) {
							frm.reload_doc();
						}
					},
					freaze: true,
					freaze_message: __("Running Employee ID Generation Method..")
				});
			});
		}
	},
	status: function(frm){
		set_mandatory(frm);
	},
    shift_working: function(frm) {
        set_shift_working_btn(frm);
        filterDefaultShift(frm);
        setProjects(frm);
        TransferToNonShift(frm);
		frm.trigger('mandatory_reports_to');
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
	},
	onload: function(frm) {
        frm.trigger('mandatory_reports_to');
		is_employee_master(frm);
    },
	designation: function(frm) {
		frm.trigger('mandatory_reports_to');
	},
	attendance_by_timesheet: function(frm) {
		frm.trigger('mandatory_reports_to');
	},
	mandatory_reports_to: function(frm){
		if (frm.doc.designation == "General Manager" || frm.doc.shift_working==1 || frm.doc.attendance_by_timesheet==1) {
            frm.set_df_property("reports_to", "reqd", 0);
        } else {
            frm.set_df_property("reports_to", "reqd", 1);
        }
	},
	under_company_residency: function(frm){
		change_employee_id(frm);
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

var change_employee_id = function(frm) {
	if(frm.doc.under_company_residency == 1){
		frappe.call({
			method: 'one_fm.overrides.employee.get_new_employee_id',
			args: {
			employee_id:frm.doc.employee_id,
			},
			callback: function (r) {
				if (r && r.message) {
					frm.set_value('employee_id',  r.message)
				}

			}
		});
	}
}
// Hide un-needed fields
const hideFields = frm => {
    $("[data-doctype='Employee Checkin']").hide();
}

let is_employee_master = frm =>{
	frappe.call({
		method: "one_fm.overrides.employee.is_employee_master",
		args: {"user": frappe.session.user},
		callback: function (r) {
			console.log(r.message)
			if (!parseInt(r.message)){
				frm.disable_form()
			}
		}

	})
	
}

let set_grd_fields= frm=>{
	frm.set_df_property('custom_employee_photo',"hidden",1)
	if(frappe.user_roles.includes("GRD Supervisor")){
		frm.set_df_property('custom_employee_photo',"hidden",0)
	}
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

function setCharAt(str,index,chr) {
    if(index > str.length-1) return str;
    return str.substring(0,index) + chr + str.substring(index+1);
}

