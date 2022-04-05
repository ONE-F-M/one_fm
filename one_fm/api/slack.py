# -*- coding: utf-8 -*-
# Copyright (c) 2022, ONEFM and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import get_url_to_form
from frappe import _
import requests
import json


error_messages = {
	400: "400: Invalid Payload or User not found",
	403: "403: Action Prohibited",
	404: "404: Channel not found",
	410: "410: The Channel is Archived",
	500: "500: Rollup Error, Slack seems to be down"
}


def send_slack_message(message):
    data = {"text": message, "attachments": []}
    try:
        default_api_integration = frappe.get_doc("Default API Integration")
        webhook = frappe.get_doc("API Integration",
            [i for i in default_api_integration.integration_setting
            if i.app_name=='Slack Issue'][0].setting)
            # attach link
        url = f'<a href="{frappe.utils.get_url()}/app/issue?status=Open">Issue List</a>'
        link_to_doc = {
			"fallback": _("See the document list at {0}").format(
                url
            ),
			"actions": [
				{
					"type": "button",
					"text": _("Go to the document"),
					"url": url,
					"style": "warning",
				}
			],
		}
        data["attachments"].append(link_to_doc)
        r = requests.post(webhook.url, data=json.dumps(data), timeout=60)
        if not r.ok:
            message = error_messages.get(r.status_code, r.status_code)
            frappe.log_error(message, _('Slack Webhook Error'))
            return 'error'

        return 'success'
    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(),
            'Slack Integration')
