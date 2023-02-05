frappe.listview_settings['Roster Employee Actions'] = {

    // set default filters
    filters: {

    },
    onload(listview){
        if (!frappe.user.has_role('Operation Admin')){
            frappe.db.get_value('Employee', {'user_id':frappe.session.user}, 'name').then(res=>{
                console.log(res.message.name)
                $('input[data-fieldname="supervisor"]')[0].value = res.message.name;
                $('button[data-original-title="Refresh"')[0].click();
                $('input[data-fieldname="supervisor"]')[0].disabled=1;
            })
        } 
        
    },
    before_render(listview) {
    },
}
