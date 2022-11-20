frappe.listview_settings['Roster Projection Checker'] = {
	onload: function (listview) {
        listview.page.add_inner_button("Create Checker for Today", function() {
            generate_checker();
        })
    },
};

const generate_checker = function(){
      frappe.call('one_fm.operations.doctype.roster_projection_checker.roster_projection_checker.generate_checker').then(r => {
          frappe.msgprint("Checker has started, records will be prepared, please check back later.")
      })
  }