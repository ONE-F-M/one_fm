import os

import frappe
from one_fm.api.slack import send_slack_message



def daily_open():
    """
        send and notifify slack about issue exceeding 2hrs since
        status was last changed to open
    """
    """
        Checks if it is the production ip or any allowed ip that is sending the request, if not, it fails silently

    """
    allowed_ip = frappe.get_doc("Default API Integration").allowed_ip_address
    allowed_ip_list = [i.address for i in allowed_ip]
    external_IP = os.popen('curl -s ifconfig.me').readline()
    if external_IP in allowed_ip_list:
        query = frappe.db.sql("""
            SELECT COUNT(status) as status_count FROM `tabIssue` WHERE status='Open' AND DATEDIFF(NOW(), modified)>0;
        """, as_dict=1)

        if query:
            # send slack message if open issues
            send_slack_message(f"There are {query} open issue(s) that have not been replied to in the last 24 hours")

    else:
        pass
