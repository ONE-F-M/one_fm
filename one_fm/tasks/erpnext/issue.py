import frappe
from one_fm.api.slack import send_slack_message



def daily_open():
    """
        send and notifify slact about issue exceeding 2hrs since
        status was last changed to open
    """
    query = len(frappe.db.sql("""
        SELECT DISTINCT v.docname FROM tabVersion v
        JOIN `tabIssue` i ON i.name=v.docname
        WHERE i.status="Open" AND v.ref_doctype='Issue'
        AND v.data LIKE '%"status"%' AND v.data LIKE '%"Open"%'
        AND DATEDIFF(NOW(), v.creation)>0;
    """, as_dict=1))
    if query:
        # send slack message if open issues
        send_slack_message(f"There are {query} open issue(s) that have not been replied to in the last 24 hours")
