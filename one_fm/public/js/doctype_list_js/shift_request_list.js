frappe.listview_settings['Shift Request'] = {
    onload: function(listview) {
        function removeWorkflowButtons(actions_menu) {
            if (actions_menu) {
                actions_menu.find('.dropdown-item').each(function() {
                    const text = $(this).text().trim();
                    if (['Approve', 'Reject', 'Return To Draft'].includes(text)) {
                        $(this).remove();
                    }
                });
            }
        }
        if (!frappe.user_roles.includes('System Manager') && !frappe.user_roles.includes('Attendance Manager')) {
            setTimeout(() => {
                const actions_menu = listview.page.actions_btn_group;
                removeWorkflowButtons(actions_menu);
            }, 200);

            listview.$result.on('change', '.list-check-all, .list-row-check', function() {
                setTimeout(() => {
                    const actions_menu = listview.page.actions_btn_group;
                    removeWorkflowButtons(actions_menu);
                }, 200);
            });
        }
    }
};