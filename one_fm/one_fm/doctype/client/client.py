# Copyright (c) 2024, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.website.website_generator import WebsiteGenerator
from frappe import _

class Client(WebsiteGenerator):
    website = frappe._dict(
        condition_field = "published",
        page_title_field = "customer",
    )
    hash = frappe.generate_hash(length=8)

    def validate(self):
        if not self.route:
            self.route_hash = self.hash
            self.route = f"client/{frappe.scrub(self.hash)}"

        if self.gst_number and len(self.gst_number) != 15:
            frappe.throw(_("GST number must be 15 characters."), frappe.ValidationError)

    def autoname(self):
        self.name = self.hash

    @frappe.whitelist(allow_guest=True)
    def get_context(self, context):
        context.title = self.customer_name
        context.id = self.route_hash
        context.allow_guest_to_view = 1



