frappe.ui.form.on('Customer', {
    refresh: function(frm) {
        dashboard_link_doctype(frm, "Operations Project");
    }
});


function dashboard_link_doctype (frm, doctype){

    var parent = $('.form-dashboard-wrapper [data-doctype="Project"]').closest('div').parent();
    
    parent.find('[data-doctype="'+doctype+'"]').remove();

    parent.append(frappe.render_template("dashboard_link_doctype", {doctype:doctype}));

    var self = parent.find('[data-doctype="'+doctype+'"]');

    set_open_count(frm, doctype);

    // bind links
    self.find(".badge-link").on('click', function() {
        frappe.route_options = {"customer": frm.doc.name}
        frappe.set_route("List", doctype);
    });

    // bind open notifications
    self.find('.open-notification').on('click', function() {
        frappe.route_options = {
            "customer": frm.doc.name,
            "status": "Draft"
        }
        frappe.set_route("List", doctype);
    });

    // bind new
    if(frappe.model.can_create(doctype)) {
        self.find('.btn-new').removeClass('hidden');
    }
    self.find('.btn-new').on('click', function() {
        frappe.new_doc(doctype,{
            "customer": frm.doc.name
        });
    });
}

function set_open_count (frm, doctype){
    
    var method = '';
    var links = {};

    if(doctype=="Operations Project"){
        method = 'one_fm.api.dashboard_utils.get_open_count';
        links = {
            'fieldname': 'customer',
            'transactions': [
                {
                    'label': __('Operations Project'),
                    'items': ['Operations Project']
                },
            ]
        };
    }

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
    <span class="open-notification hidden" title="{{ __("Open {0}", [__(doctype)])}}"></span> \
        <button class="btn btn-new btn-default btn-xs hidden" data-doctype="{{ doctype }}"> \
                <i class="octicon octicon-plus" style="font-size: 12px;"></i> \
        </button>\
    </div>';