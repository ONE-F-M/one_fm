
frappe.ui.form.on('Project', {
    refresh(frm) {
        frm.set_df_property('project_type', 'reqd', true);
        if (frm.doc.project_type === "External") {
            const pocField = cur_frm.get_field("poc").grid;
            pocField.toggle_reqd("poc", true);
            pocField.toggle_reqd("designation", true);
        }
        if (!frm.doc.__islocal && frm.doc.project_type === "External") {
            remove_existing_sections();
            add_dashboard_sections(frm);
        }
        frm.set_query("income_account", () => ({
            filters: { root_type: 'Income', is_group: 0 }
        }));
        frm.set_query("cost_center", () => ({
            filters: { is_group: 0 }
        }));
        frm.refresh_field("income_account");
        frm.refresh_field("cost_center");
    },
    before_save(frm) {
        validate_linked_schedules(frm);
    }
});

function remove_existing_sections() {
    ["Project Structure", "Operations Action", "Communication"].forEach(section => {
        $(`[data-onefm="${section}"]`).remove();
    });
}

function add_dashboard_sections(frm) {
    const sections = [
        {
            title: "Project Structure",
            doctypes: ["Operations Site", "Operations Shift"]
        },
        {
            title: "Operations Action",
            doctypes: ["MOM"]
        },
        {
            title: "Communication",
            doctypes: ["Contracts"]
        }
    ];
    sections.forEach(({ title, doctypes }) => {
        create_dashboard_section("Timesheet", title);
        doctypes.forEach(dt => dashboard_link_doctype(frm, dt, title));
    });
}


function create_dashboard_section(data_doctype, title) {
    const parent = $(`.form-dashboard-wrapper [data-doctype="${data_doctype}"]`).closest('div.row');
    parent.append(`<div class="col-xs-6" data-onefm="${title}"><h6>${title}</h6></div>`);
}

function dashboard_link_doctype(frm, doctype, data_onefm) {
    const parent = $(`[data-onefm="${data_onefm}"]`);
    parent.find(`[data-doctype="${doctype}"]`).remove();
    parent.append(frappe.render_template("dashboard_link_doctype", { doctype }));
    const self = parent.find(`[data-doctype="${doctype}"]`);

    set_open_count(frm, doctype);

    // Bind links
    self.find(".badge-link").on('click', () => {
        frappe.route_options = { project: frm.doc.name };
        frappe.set_route("List", doctype);
    });

    // Bind open notifications
    self.find('.open-notification').on('click', () => {
        frappe.route_options = {
            project: frm.doc.name,
            status: "Draft"
        };
        frappe.set_route("List", doctype);
    });

    // Bind new
    if (frappe.model.can_create(doctype)) {
        self.find('.btn-new').removeClass('hidden');
    }
    self.find('.btn-new').on('click', () => {
        frappe.new_doc(doctype, { project: frm.doc.name });
    });
}


function set_open_count(frm, doctype) {
    const method = 'one_fm.api.dashboard_utils.get_open_count';
    const links = {
        fieldname: 'project',
        transactions: [
            {
                label: __(doctype),
                items: [doctype]
            }
        ]
    };

    frappe.call({
        type: "GET",
        method,
        args: {
            doctype: frm.doctype,
            name: frm.doc.name,
            links
        },
        callback(r) {
            // update badges if possible
            if (frm.dashboard && typeof frm.dashboard.set_badge_count === "function") {
                (r.message.count || []).forEach(d => {
                    frm.dashboard.set_badge_count(d.name, cint(d.open_count), cint(d.count));
                });
            }
        }
    });
}

function validate_linked_schedules (frm) {
    if (frm.doc.is_active === 'No' && !frm.__confirmed_inactive && !frm.is_new()) {
        frappe.call({
            method: "one_fm.one_fm.project_custom.check_existing_schedules",
            args: {
                project: frm.doc.name
            },
            callback: function(response) {
                if (response.message && response.data_obj && response.data_obj.is_exist) {
                    frappe.confirm(
                        "The future Employee Schedules linked to the Project will be deleted on confirmation. Do you want to proceed?",
                        function () {
                            frappe.call({
                                method: "one_fm.one_fm.project_custom.delete_future_schedules",
                                args: {
                                    project: frm.doc.name
                                },
                                freeze: true,
                                freeze_message: __("Deleting Linked Schedules..."),
                                callback: function() {
                                    frm.__confirmed_inactive = true;
                                    frm.save();
                                }
                            });
                        },
                        function () {
                            frappe.validated = false;
                            frm.reload_doc();
                        }
                    );
                } else {
                    frappe.validated = true
                }
            }
        });
        frappe.validated = false
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
