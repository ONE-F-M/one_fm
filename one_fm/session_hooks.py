from werkzeug.wrappers import Request, Response
import frappe

def on_login(login_manager):
    """
        Process some actions when user logins in.
        Created log when admin logs in.
    """
    pass


def boot_session(bootinfo):
	"""Send each Workflow State's style to the desk so list pills take its colour."""
	states = frappe.get_all("Workflow State", fields=["name", "style"], filters={"style": ["is", "set"]})
	bootinfo.workflow_state_styles = {row.name: row.style for row in states}
