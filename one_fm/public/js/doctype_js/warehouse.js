frappe.ui.form.on('Warehouse', {
  refresh: function(frm){
    frm.toggle_enable(['is_group'], true);
		frm.set_query('one_fm_site', function () {
			return {
				filters: {
					'project': frm.doc.one_fm_project
				}
			};
		});
		frm.set_query('one_fm_location', function () {
			return {
				filters: {
					'project': frm.doc.one_fm_project
				}
			};
		});
    unsetCustomer(frm);    
  },
	status: function(frm) {
		if(frm.doc.status == 'Enable'){
			frm.set_value("disabled", 0);
		}
		else{
			frm.set_value("disabled", 1);
		}
	},
  one_fm_project: function(frm) {
    if(frm.doc.one_fm_project){
      frappe.call({
        method: 'frappe.client.get',
        args: {
          doctype: 'Project',
          name: frm.doc.one_fm_project
        },
        callback: function(r) {
          if(r && r.message){
            var project = r.message;
            if(project.project_sites && project.project_sites.length > 0){
              frm.set_value('one_fm_site', project.project_sites[0].site);
            }
          }
        }
      })
    }
  },
  one_fm_site: function(frm) {
    if(frm.doc.one_fm_site){
      frappe.call({
        method: 'frappe.client.get',
        args: {
          doctype: 'Operations Site',
          name: frm.doc.one_fm_site
        },
        callback: function(r) {
          if(r && r.message){
            var site = r.message;
            if(site.site_location){
              frm.set_value('one_fm_location', site.site_location);
            }
          }
        }
      })
    }
  },
  one_fm_is_project_warehouse: function(frm) {
    if(!frm.doc.one_fm_is_project_warehouse){
      frm.set_value('one_fm_project', '');
      frm.set_value('one_fm_site', '');
    }
  },

  customer: function(frm){
    if (frm.doc.customer){
      frm.set_query('one_fm_project', function () {
        return {
          filters: {
            'customer': frm.doc.customer
          }
        };
      });
  } else {
    unsetCustomer(frm);
  }
  },

});

var unsetCustomer = frm => {
  frm.set_query('one_fm_project', function () {
    return {
      filters: [
        ['customer', 'in', ["", null]]
      ]
    };
  });
}