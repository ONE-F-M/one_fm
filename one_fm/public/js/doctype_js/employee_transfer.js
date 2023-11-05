frappe.ui.form.on("Employee Transfer", {
	new_project: function(frm) {
        frm.set_query('new_site', () => {return { filters: {project: frm.doc.new_project } }});
        set_transfer_details(frm, 'project', 'Project', frm.doc.current_project, frm.doc.new_project);
	},
	new_site: function(frm) {
            frm.set_query('new_shift', () => {return { filters: {site: frm.doc.new_site } }});
            set_transfer_details(frm, 'site', 'Site', frm.doc.current_site, frm.doc.new_site);
    },
	new_shift: function(frm) {
            set_transfer_details(frm, 'shift', 'Shift', frm.doc.current_shift, frm.doc.new_shift);
    }
});


const set_transfer_details = (frm, fieldname, property, current_value, new_value) => {

    if (new_value){

        if (frm.doc.transfer_details.length){
            let found = frm.doc.transfer_details.filter(item => item.fieldname === fieldname);
            console.log()
            if (found.length){
                found[0].current = current_value;
                found[0].new = new_value;
                found[0].property = property;
                frm.refresh_field('transfer_details');
            } else {
                frm.add_child('transfer_details', {
                    current: current_value,
                    new: new_value,
                    property: property,
                    fieldname: fieldname
                });
                frm.refresh_field('transfer_details');
            }
        } else {
            frm.add_child('transfer_details', {
                current: current_value,
                new: new_value,
                property: property,
                fieldname: fieldname
            });
            frm.refresh_field('transfer_details');
        }
    }
}