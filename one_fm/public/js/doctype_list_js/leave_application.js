frappe.listview_settings["Leave Application"] = {
    onload: function (list_view) {
        if(frappe.user_roles.includes("System Manager")){
            list_view.page.add_inner_button(__("Approve Leaves Without Attachment"), function () {
                frappe.confirm(
                    __('Are you sure you want to approve all pending sick leaves?  <br/> Please note \
                    that to reverse this action the leave document must be cancelled.',),
                    function(){
                        // Yes
                        frappe.call({
                            freeze:true,
                            freeze_message:"Closing Sick Leaves",
                            method: 'one_fm.overrides.leave_application.fix_sick_leave',
                            callback(r) {
                                ;
                            },
                            
                        });
                    },
                    function(){} // No
                );
            })
        }
        
    }
}
