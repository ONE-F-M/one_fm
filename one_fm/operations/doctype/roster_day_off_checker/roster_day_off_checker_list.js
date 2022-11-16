frappe.listview_settings['Roster Day Off Checker'] = {
	onload: function (listview) {
        listview.page.add_inner_button("Create Checker for Today", function() {
            generate_checker();
        })
    },
};

const generate_checker = function(){
      frappe.call('one_fm.operations.doctype.roster_day_off_checker.roster_day_off_checker.generate_checker').then(r => {
          frappe.msgprint("Checker has started, records will be prepared, please check back later.")
      })
  }