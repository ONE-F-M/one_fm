from frappe.oauth import *

class OAuthWebRequestValidatorOverride(OAuthWebRequestValidator):
    """
    Overwrite the oauth token validator in frappe framework
    """

    def validate_bearer_token(self, token, scopes, request):
		# Remember to check expiration and scope membership
        otoken = frappe.get_doc("OAuth Bearer Token", token)
        token_expiration_local = otoken.expiration_time.replace(
            tzinfo=pytz.timezone(get_system_timezone())
        )
        token_expiration_utc = token_expiration_local.astimezone(pytz.utc)
        is_token_valid = (
            frappe.utils.datetime.datetime.utcnow().replace(tzinfo=pytz.utc) < token_expiration_utc
        ) and otoken.status != "Revoked"
        client_scopes = frappe.db.get_value("OAuth Client", otoken.client, "scopes").split(
            get_url_delimiter()
        )
        are_scopes_valid = True
        for scp in scopes:
            are_scopes_valid = are_scopes_valid and True if scp in client_scopes else False

        return is_token_valid and are_scopes_valid