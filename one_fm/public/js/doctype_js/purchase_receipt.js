frappe.ui.form.on('Purchase Receipt', {
    onload_post_render: function(frm) {
        set_readonly_for_warehouse_users(frm);
        hide_finance_fields_for_non_finance_users(frm);
    },
    
    refresh: function(frm) {
        // frappe.after_ajax ensures all grid DOM elements are fully loaded
        frappe.after_ajax(() => {
            set_readonly_for_warehouse_users(frm);
            hide_finance_fields_for_non_finance_users(frm);
        });
    }
});

frappe.ui.form.on('Purchase Receipt Item', {
    form_render: function(frm, cdt, cdn) {
        set_readonly_for_warehouse_users(frm);
        hide_finance_fields_for_non_finance_users(frm);
    },
    items_add: function(frm) {
        set_readonly_for_warehouse_users(frm);
        hide_finance_fields_for_non_finance_users(frm);
    }
});

/**
 * Sets specific pricing fields in the Purchase Receipt Item grid as read-only for users with warehouse or stock-related roles.
 *
 * @param {frappe.ui.Form} frm - The current Purchase Receipt form instance.
 *
 * Business Logic:
 * - Users with any of the following roles: 'Warehouse Maintainer', 'Warehouse Supervisor', 'Stock Issuer', 'Stock Manager', or 'Stock User'
 *   (excluding users who only have default roles such as 'Assignee', 'Penalty Recipient', 'Employee', or 'Employee Self Service')
 *   are restricted from editing pricing-related fields in the Purchase Receipt Item grid.
 * - The affected fields are: 'rate', 'amount', 'discount_percentage', 'discount_amount', and 'distributed_discount_amount'.
 *
 * Business Rationale:
 * - This restriction ensures that warehouse and stock staff, whose responsibilities are operational (e.g., handling goods and stock),
 *   cannot modify pricing or discount information, which should be controlled by purchasing or finance personnel.
 * - Prevents unauthorized or accidental changes to financial data by users whose roles do not require such access.
 */
function set_readonly_for_warehouse_users(frm) {
    const default_roles = [
        'Assignee',
        'Penalty Recipient',
        'Employee',
        'Employee Self Service',
        'All', 
        'Guest',
        'Desk User'
    ];
    
    const warehouse_stock_roles = [
        'Warehouse Maintainer',
        'Warehouse Supervisor',
        'Stock Issuer',
        'Stock Manager',
        'Stock User'
    ];
    
    const readonly_fields = [
        'rate',
        'amount',
        'discount_percentage',
        'discount_amount',
        'distributed_discount_amount'
    ];
    
    // Get all roles excluding default roles
    const non_default_roles = frappe.user_roles.filter(role => 
        !default_roles.includes(role)
    );

    // Check if user has warehouse roles
    const has_warehouse_role = non_default_roles.some(role => 
        warehouse_stock_roles.includes(role)
        
    );

    
    // Get roles that are neither default nor warehouse
    const other_roles = non_default_roles.filter(role => 
        !warehouse_stock_roles.includes(role)
    );
    
    // Make read-only ONLY if user has warehouse role BUT no other roles
    if (has_warehouse_role && other_roles.length === 0) {
        readonly_fields.forEach(field => {
            frm.fields_dict.items.grid.update_docfield_property(
                field,
                'read_only',
                1
            );
        });
        
        frm.refresh_field('items');
    }
}





/**
 * Story 7: Restrict visibility of pricing/tax fields on Purchase Receipt to authorized roles
 */
function hide_finance_fields_for_non_finance_users(frm) {
    const allowed_roles = [
        'Finance User', 
        'Finance Manager', 
        'Director', 
        'Purchase User', 
        'Purchase Manager', 
        'Purchase Master Manager', 
        'System Manager', 
        'Finance PO Approver', 
        'Junior Accounts User'
    ];
    
    const has_allowed_role = frappe.user_roles.some(role => allowed_roles.includes(role));
    
    if (!has_allowed_role) {
        // Child fields to hide
        const child_fields = [
            'rate', 'price_list_rate', 'base_rate', 'base_price_list_rate', 'net_rate', 'base_net_rate', 'amount', 'base_amount', 'net_amount', 
            'base_net_amount', 'discount_percentage', 'discount_amount', 'margin_type', 
            'margin_rate_or_amount', 'rate_with_margin', 'base_rate_with_margin'
        ];
        
        child_fields.forEach(field => {
            // Update the core meta so the child modal dialog instantly respects the hidden property
            let df = frappe.meta.get_docfield('Purchase Receipt Item', field);
            if (df) {
                df.hidden = 1;
            }
            // Also update the visual grid instance
            if (frm.fields_dict.items && frm.fields_dict.items.grid) {
                frm.fields_dict.items.grid.update_docfield_property(field, 'hidden', 1);
            }
        });
        
        // Header fields to hide
        const header_fields = [
            'total', 'net_total', 'base_total', 'base_net_total', 
            'grand_total', 'base_grand_total', 'rounded_total', 
            'base_rounded_total', 'in_words', 'base_in_words', 
            'taxes_and_charges_added', 'taxes_and_charges_deducted', 
            'total_taxes_and_charges', 'taxes_section', 'taxes',
            'totals_section', 'discount_section', 'sec_tax_breakup',
            'other_charges_calculation'
        ];
        
        frm.toggle_display(header_fields, false);
        
        // Force refresh grid if drawn
        if (frm.fields_dict.items.grid) {
            frm.refresh_field('items');
        }
    }
}
