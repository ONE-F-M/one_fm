import frappe
from frappe.integrations.oauth2 import revoke_token

def revoke_and_delete_existing_tokens(doc, event):
    """
        Revokes and deletes all the existing tokens for the target user.
    """
    user_existing_tokens = frappe.get_all('OAuth Bearer Token', filters={'user': doc.user}, fields=['name'])

    for token in user_existing_tokens:
        # Check if its not the recently generated token
        if(token.name != doc.name):
            revoke_token(token=token.name)
            frappe.delete_doc('OAuth Bearer Token', token.name,ignore_permissions=True)
