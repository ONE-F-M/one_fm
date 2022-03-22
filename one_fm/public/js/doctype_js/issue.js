frappe.ui.form.on('Issue', {
    refresh:function(frm){
      // set pivotal tracker button
      pivotal_tracker_button(frm);
      add_pivotal_section(frm);
      set_issue_type_filter(frm);
    },
    department: function(frm) {
      set_issue_type_filter(frm);
    }
});

var set_issue_type_filter = frm => {
  var filters = {};
  if(frm.doc.department){
    filters['department'] = frm.doc.department;
  }
  frm.set_query("issue_type", function() {
    return {
      query: "one_fm.utils.get_issue_type_in_department",
      filters: filters
    }
  });
};


let pivotal_tracker_button = frm => {

  if(frm.doc.status=='Open' && frappe.user.has_role('System Manager') && !frm.doc.pivotal_tracker){
    frm.add_custom_button('Pivotal Tracker', () => {
      frappe.confirm('Are you sure you create Pivotal Tracker story?',
        () => {
            // action to perform if Yes is selected
            frappe.call({
                method: "one_fm.api.doc_methods.issue.log_pivotal_tracker", //dotted path to server method
                freeze_message: 'Logging story to Pivotal Tracker',
                args:frm.doc,
                callback: function(r) {
                    // code snippet
                    if(r.message.status=='success'){
                      frappe.msgprint("Pivotal Tracker story created successfully");
                      frm.refresh();
                      frm.reload_doc();
                    }
                }
            })
        }, () => {
            // action to perform if No is selected
        }
      )
    }, 'Create')
  }
}


let add_pivotal_section = frm => {
  if(frm.doc.status=='Open' && frappe.user.has_role('System Manager')
    && frm.doc.pivotal_tracker && !document.querySelector('#pivotal_tracker_span')){
    let el = `
    <span id="pivotal_tracker_span">Issue have been logged to Pivotal tracker</span><br>
    <a href="${frm.doc.pivotal_tracker}" class="btn btn-primary" target="_blank">Pivotal Tracker</a>
    `;
    frm.dashboard.add_section(el, __("Pivotal Tracker"))
  }
}
