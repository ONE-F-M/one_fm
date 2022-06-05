import frappe


def execute():
    add_shift_assignment_permissions()


def add_shift_assignment_permissions():
    """
        Add shift assignment permission every migrate
    """
    print('Updating Shift Assignment Permissions for:')
    roles = ['Employee', 'HR Manager', 'HR User']
    shift_assignment = frappe._dict({
         'parent': 'Shift Assignment',
         'parentfield': 'permissions',
         'parenttype': 'DocType',
         'role': '',
         'if_owner': 0,
         'permlevel': 0,
         'select': 0,
         'read': 1,
         'write': 0,
         'create': 0,
         'delete': 0,
         'submit': 0,
         'cancel': 0,
         'amend': 0,
         'report': 0,
         'export': 0,
         'import': 0,
         'set_user_permissions': 0,
         'share': 0,
         'print': 0,
         'email': 0,
         'doctype': 'Custom DocPerm'
    })

    for role in roles:
        if not frappe.db.exists("Custom DocPerm", {
            'role':role,
            'parent': 'Shift Assignment',
            'parentfield': 'permissions',
            'parenttype': 'DocType',
            }):
            print(role)
            perm = frappe.get_doc(shift_assignment)
            perm.role = role
            if role in ['HR Manager', 'HR User']:
                perm.write = 1
                perm.create = 1
                perm.delete = 1
                perm.submit = 1
                perm.cance = 1
            perm.insert(ignore_permissions=1)
