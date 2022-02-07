frappe.ui.form.on('Project', {
    refresh: function(frm) {
        frm.set_df_property('project_type', 'reqd', true);
        if(!frm.doc.__islocal && frm.doc.project_type === "External"){
            remove_existing();
            let data_onefm = "Project Structure";
            create_dashboard_section("Timesheet", data_onefm);
            dashboard_link_doctype(frm, "Operations Site", data_onefm);
            dashboard_link_doctype(frm, "Operations Shift", data_onefm);
            
            data_onefm = "Operations Action";
            create_dashboard_section("Timesheet", data_onefm);
            dashboard_link_doctype(frm, "MOM", data_onefm);

            data_onefm = "Communication";
            create_dashboard_section("Timesheet", data_onefm);
            dashboard_link_doctype(frm, "Contracts", data_onefm);
        }
        frm.set_query("income_account", function() {
            return {
                filters:{
                    root_type:'Income',
                    is_group: 0
                }
            };
        });
        frm.set_query("cost_center", function() {
            return {
                filters:{
                    is_group: 0
                }
            };
        });
        frm.refresh_field("income_account");
        frm.refresh_field("cost_center");
    }
});

// Remove existing sections
function remove_existing(){
    $(`[data-onefm="Project Structure"]`).remove();
    $(`[data-onefm="Operations Action"]`).remove();
    $(`[data-onefm="Communication"]`).remove();
}

function create_dashboard_section(data_doctype, title){
    let parent = $(`.form-dashboard-wrapper [data-doctype="${data_doctype}"]`).closest('div.row');
    parent.append(`<div class="col-xs-6" data-onefm="${title}"><h6>${title}</h6></div>`);
    console.log(parent);
}

function dashboard_link_doctype (frm, doctype, data_onefm){

    let parent = $(`[data-onefm="${data_onefm}"]`);    
    parent.find(`[data-doctype="${doctype}"]`).remove();
    parent.append(frappe.render_template("dashboard_link_doctype", {doctype}));
    let self = parent.find(`[data-doctype="${doctype}"]`);


    set_open_count(frm, doctype);

    // bind links
    self.find(".badge-link").on('click', function() {
        frappe.route_options = {"project": frm.doc.name}
        frappe.set_route("List", doctype);
    });

    // bind open notifications
    self.find('.open-notification').on('click', function() {
        frappe.route_options = {
            "project": frm.doc.name,
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
            "project": frm.doc.name
        });
    });
}

function set_open_count (frm, doctype){
    
    let method = '';
    let links = {};

    method = 'one_fm.api.dashboard_utils.get_open_count';
    links = {
        'fieldname': 'project',
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
    <span class="open-notification hidden" title="{{ __("Open {0}", [__(doctype)])}}"></span> \
        <button class="btn btn-new btn-default btn-xs hidden" data-doctype="{{ doctype }}"> \
                <i class="octicon octicon-plus" style="font-size: 12px;"></i> \
        </button>\
    </div>';