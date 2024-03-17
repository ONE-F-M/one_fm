import frappe
import requests
from frappe.utils import get_url


def revoke_token(access_token):

    url = f"{get_url()}/api/method/frappe.integrations.oauth2.revoke_token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {"token": access_token}

    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        return True

    except requests.exceptions.RequestException as e:
        print(f"Error revoking token: {e}")
        return False


def revoke_and_delete_existing_tokens(doc, event):
    """
        Revokes and deletes all the existing tokens for the target user.
    """
    user_existing_tokens = frappe.get_all('OAuth Bearer Token', filters={
                                          'client': doc.client, 'user': doc.user, 'status': 'Active', 'name': ['!=', doc.name]}, fields=['name'])

    for token in user_existing_tokens:
        revoke_token(token.name)
