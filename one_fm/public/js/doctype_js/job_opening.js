// this.frm.dashboard.add_transactions([
//     {
//       'items': ['Job Opening Add']
//     }
// ]);

frappe.ui.form.on('Job Opening', {
  refresh(frm) {
    set_my_dash_board(frm);
    frm.set_query('agency', 'one_fm_active_willing_agency', function(doc) {
      return {
        filters: {
          'active': true
        }
      }
    });
  },
  one_fm_job_post_valid_till: function(frm) {
    validate_date(frm);
  },
  publish: function(frm) {
    if(!frm.doc.publish && frm.doc.allow_easy_apply){
      frm.set_value('allow_easy_apply', false);
    }
  }
});

var validate_date = function(frm) {
	if(frm.doc.one_fm_job_post_valid_till < frm.doc.one_fm_job_opening_created){
		frappe.throw(__("Job Post Valid Till Date cannot be before Job Opening Created Date"));
	}
	if(frm.doc.one_fm_job_post_valid_till < frappe.datetime.now_date()){
		frappe.throw(__("Job Post Valid Till Date cannot be before Today"));
	}
};

var set_my_dash_board = function(frm) {
	dashboard_link_doctype(frm, "Note", 'one_fm_job_opening');
	// dashboard_link_doctype(frm, "Job Opening Add", 'job_opening');

	// Hide + button
	if(frm.doc.disabled){
			let db_btns = $('.form-dashboard-wrapper').find('.btn-new').find('.btn-new');
			$.each(db_btns.prevObject, function(i, d) {
					$(d).hide();
			});
	}
};

var dashboard_link_doctype = function (frm, doctype, fieldname){
	var parent = $('.form-dashboard-wrapper [data-doctype="Job Applicant"]').closest('div').parent();
	parent.find('[data-doctype="'+doctype+'"]').remove();
	parent.append(frappe.render_template("dashboard_link_doctype", {doctype:doctype}));
	var self = parent.find('[data-doctype="'+doctype+'"]');
	set_open_count(frm, doctype, fieldname);

	var route_options_filters = {"job_opening": frm.doc.name};
	if(fieldname.includes('one_fm')){
		route_options_filters = {"one_fm_job_opening": frm.doc.name};
	}

	// bind links
	self.find(".badge-link").on('click', function() {
		frappe.route_options = route_options_filters;
		frappe.set_route("List", doctype);
	});

	// bind open notifications
	self.find('.open-notification').on('click', function() {
		frappe.route_options = route_options_filters;
		frappe.set_route("List", doctype);
	});

	// bind new
	if(frappe.model.can_create(doctype)) {
		self.find('.btn-new').removeClass('hidden');
	}
	self.find('.btn-new').on('click', function() {
		frappe.new_doc(doctype, route_options_filters);
	});
};

function set_open_count (frm, doctype, fieldname){

    let method = '';
    let links = {};

    method = 'one_fm.api.dashboard_utils.get_open_count';
    links = {
        'fieldname': fieldname,
        'transactions': [
            {
                'label': __(doctype),
                'items': [doctype]
            },
        ]
    };

    if(method!=""){
        frappe.call({
            type: "GET",
            method: method,
            args: {
                doctype: frm.doctype,
                name: frm.doc.name,
                links: links,
            },
            callback: function(r) {
                // update badges
                $.each(r.message.count, function(i, d) {
                    frm.dashboard.set_badge_count(d.name, cint(d.open_count), cint(d.count));
                });
            }
        });
    }
}

frappe.templates["dashboard_link_doctype"] = ' \
<div class="document-link" data-doctype="{{ doctype }}"> \
<a class="badge-link small">{{ __(doctype) }}</a> \
<span class="text-muted small count"></span> \
<span class="open-notification hidden" title="{{ __("List {0}", [__(doctype)])}}"></span> \
<button class="btn btn-new btn-default btn-xs hidden" data-doctype="{{ doctype }}"> \
<i class="octicon octicon-plus" style="font-size: 12px;"></i> \
</button>\
</div>';
