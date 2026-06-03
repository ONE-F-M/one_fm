// Copyright (c) 2020, ONE FM and contributors
// For license information, please see license.txt

// ── Status options per process name ──────────────────────────────────────────
var STATUS_MAP = {
  "Job Offer Issuance": ["Pending", "Offer Accepted", "Rejected"],
  "Visa Processing": ["Pending", "Applied", "Issued", "Rejected"],
  "Medical Test": ["Pending", "In Process", "Fit", "Unfit", "Passed", "Failed"],
  "Remedical Test": ["Pending", "Skipped", "In Process", "Fit", "Unfit", "Passed", "Failed"],
  "PCC Clearance": ["Pending", "Applied", "Issued", "Rejected"],
  "Visa Stamping": ["Pending", "Applied", "Issued", "Approved", "Rejected"],
  "Arrival & Deployment": ["Pending", "Arriving", "Completed"]
};

frappe.ui.form.on('Candidate Country Process', {
  agency_country_process: function(frm) {
    set_country_process_details(frm);
  },
  refresh: function(frm) {
    candidate_country_process_flow_btn(frm);
    setup_inline_status_filter(frm);

    // Hide Seq Type column — defined per-row, not needed in grid view
    if (frm.fields_dict['agency_process_details']) {
      frm.fields_dict['agency_process_details'].grid.set_column_disp('sequence_type', false);
    }

    if (!frm.is_new()) {
      // ── "Apply Visa" button: manually trigger PAM Visa creation ──
      add_apply_visa_button(frm);

      // ── "Open Record" link on each child row that has reference_name ──
      setup_open_record_links(frm);
    }
  }
});

frappe.ui.form.on('Candidate Country Process Details', {
  // ── Expanded row edit form: filter status options ──
  form_render: function(frm, cdt, cdn) {
    var row = locals[cdt][cdn];
    var options = STATUS_MAP[row.process_name] || ["Pending", "In Process", "Completed"];
    var grid_row = frm.fields_dict.agency_process_details.grid.grid_rows_by_docname[cdn];
    if (grid_row && grid_row.grid_form) {
      var status_field = grid_row.grid_form.fields_dict.status;
      if (status_field) {
        status_field.df.options = options.join('\n');
        status_field.refresh();
      }
    }
  },

  // ── Validate status on change ──
  status: function(frm, cdt, cdn) {
    var row = locals[cdt][cdn];
    var allowed = STATUS_MAP[row.process_name];
    if (allowed && !allowed.includes(row.status)) {
      frappe.msgprint({
        title: __('Invalid Status'),
        message: __('"{0}" is not valid for {1}. Allowed: {2}',
          [row.status, row.process_name, allowed.join(', ')]),
        indicator: 'red'
      });
      frappe.model.set_value(cdt, cdn, 'status', 'Pending');
    }
  }
});

// ── Inline grid: intercept click on status cell and filter <select> options ──
var setup_inline_status_filter = function(frm) {
  var grid = frm.fields_dict.agency_process_details;
  if (!grid || !grid.grid || !grid.grid.wrapper) return;

  grid.grid.wrapper.off('click.status_filter').on('click.status_filter',
    '.frappe-control[data-fieldname="status"]', function() {
      var $cell = $(this);
      var $row = $cell.closest('.rows .frappe-control').length
        ? $cell.closest('[data-name]')
        : $cell.closest('.grid-row');
      if (!$row.length) {
        $row = $cell.closest('[data-name]');
      }
      var docname = $row.attr('data-name');
      if (!docname) return;

      var row_data = locals['Candidate Country Process Details'][docname];
      if (!row_data) return;

      var allowed = STATUS_MAP[row_data.process_name]
        || ["Pending", "In Process", "Completed"];

      // Wait for Frappe to render the <select>, then filter it
      setTimeout(function() {
        var $select = $cell.find('select');
        if (!$select.length) return;

        var current_val = $select.val();
        $select.find('option').each(function() {
          var opt_val = $(this).val();
          if (opt_val && !allowed.includes(opt_val)) {
            $(this).remove();
          }
        });
        // Restore current value if still valid
        if (allowed.includes(current_val)) {
          $select.val(current_val);
        }
      }, 50);
    }
  );
};

var set_country_process_details = function(frm) {
  if(frm.doc.agency_country_process){
    frm.doc.agency_process_details = [];
    frappe.model.with_doc("Agency Country Process", frm.doc.agency_country_process, function() {
      var agency_country_process= frappe.model.get_doc("Agency Country Process", frm.doc.agency_country_process)
      $.each(agency_country_process.agency_process_details, function(index, row){
        var d = frm.add_child("agency_process_details");
        d.process_name = row.process_name;
        d.responsible = row.responsible;
        d.duration_in_days = row.duration_in_days;
        d.before_task = row.before_task || '';
        d.sequence_type = row.sequence_type || 'Sequential';
        d.after_task = row.after_task || '';
        d.attachment_required = row.attachment_required;
        d.notes_required = row.notes_required;
        d.reference_type = row.reference_type;
        d.reference_complete_status_field = row.reference_complete_status_field;
        d.reference_complete_status_value = row.reference_complete_status_value;
      });
      
      frm.refresh_field("agency_process_details");
    });
  }
};

var candidate_country_process_flow_btn = function(frm) {
  if(!frm.doc.__islocal && frm.doc.name){
    frappe.call({
      doc: frm.doc,
      method:"get_workflow",
      callback: function(data){
        if(!data.exc){
          var workflow_list = data.message;
          workflow_list.forEach(function(workflow_doctype, i) {
            if(frm.doc.doctype != workflow_doctype.doctype){
              frm.add_custom_button(__(workflow_doctype.doctype), function() {
                if (!("new_doc" in workflow_doctype)){
                  var doclist = frappe.model.sync(workflow_doctype);
                  frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
                }
                else{
                  frappe.route_options = {
                    "candidate_country_process": frm.doc.name
                  };
                  frappe.new_doc(workflow_doctype.doctype);
                }
              },__("Country Process Flow"));
            }
          });
        }
      }
    });
  }
};

// ── "Apply Visa" button: manually create a PAM Visa from the tracker ─────────
var add_apply_visa_button = function(frm) {
  // Find the Visa Processing row
  var visa_row = (frm.doc.agency_process_details || []).find(function(r) {
    return r.process_name === "Visa Processing";
  });

  if (!visa_row) return;

  // Only show button if no PAM Visa is linked yet
  if (visa_row.reference_name) {
    // Already linked — show "Open PAM Visa" instead
    frm.add_custom_button(__('Open PAM Visa'), function() {
      frappe.set_route('Form', 'PAM Visa', visa_row.reference_name);
    }, __('Visa'));
  } else {
    // Check if Job Offer is accepted (prerequisite)
    var jo_row = (frm.doc.agency_process_details || []).find(function(r) {
      return r.process_name === "Job Offer Issuance";
    });
    var jo_done = jo_row && jo_row.status === "Offer Accepted";

    if (jo_done) {
      frm.add_custom_button(__('Apply Visa'), function() {
        frappe.confirm(
          __('Create a new PAM Visa application for <b>{0}</b>?', [frm.doc.candidate_name]),
          function() {
            frappe.call({
              method: 'frappe.client.save',
              args: {
                doc: {
                  doctype: 'PAM Visa',
                  candidate_country_process: frm.doc.name
                }
              },
              freeze: true,
              freeze_message: __('Creating PAM Visa...'),
              callback: function(r) {
                if (r.message) {
                  // Update the tracker row with the reference
                  frappe.model.set_value(
                    visa_row.doctype, visa_row.name,
                    'reference_name', r.message.name
                  );
                  frm.dirty();
                  frm.save().then(function() {
                    frappe.show_alert({
                      message: __('PAM Visa {0} created', [r.message.name]),
                      indicator: 'green'
                    });
                    frappe.set_route('Form', 'PAM Visa', r.message.name);
                  });
                }
              }
            });
          }
        );
      }, __('Visa'));

      // Highlight the button in primary color
      frm.change_custom_button_type(__('Apply Visa'), __('Visa'), 'primary');
    }
  }
};

// ── "Open Record" links: clickable reference_name in child rows ──────────────
var setup_open_record_links = function(frm) {
  var grid = frm.fields_dict.agency_process_details;
  if (!grid || !grid.grid || !grid.grid.wrapper) return;

  // Use event delegation — intercept clicks on the reference_name column
  grid.grid.wrapper.off('click.open_record').on('click.open_record',
    '.frappe-control[data-fieldname="reference_name"]', function(e) {
      var $cell = $(this);
      var $row = $cell.closest('[data-name]');
      var docname = $row.attr('data-name');
      if (!docname) return;

      var row_data = locals['Candidate Country Process Details'][docname];
      if (!row_data || !row_data.reference_type || !row_data.reference_name) return;

      e.stopPropagation();
      e.preventDefault();
      frappe.set_route('Form', row_data.reference_type, row_data.reference_name);
    }
  );

  // Style the reference_name cells as clickable links
  setTimeout(function() {
    (frm.doc.agency_process_details || []).forEach(function(row) {
      if (row.reference_name && row.reference_type) {
        var $row_el = grid.grid.wrapper.find('[data-name="' + row.name + '"]');
        var $ref_cell = $row_el.find('.frappe-control[data-fieldname="reference_name"] .static-area');
        if ($ref_cell.length && !$ref_cell.hasClass('linked')) {
          $ref_cell.css({
            'color': 'var(--primary-color, #2490EF)',
            'cursor': 'pointer',
            'text-decoration': 'underline'
          }).addClass('linked');
        }
      }
    });
  }, 300);
};
