# Copyright (c) 2024, ONE FM and contributors
# For license information, please see license.txt

import frappe
import re
from frappe.website.website_generator import WebsiteGenerator
from frappe import _

class Client(WebsiteGenerator):
    website = frappe._dict(
        condition_field = "published",
        page_title_field = "customer",
    )
    hash = frappe.generate_hash(length=8)

    def validate(self):
        self.validate_gst_number()
        if not self.route:
            self.route_hash = self.hash
            self.route = f"client/{frappe.scrub(self.hash)}"

    def validate_gst_number(self):
        """Validate GST Number format and uniqueness"""
        if not self.gst_number:
            return
        
        # Remove spaces and convert to uppercase
        self.gst_number = self.gst_number.replace(' ', '').upper()
        
        # GST number format validation (15 characters, alphanumeric)
        # Format: 2 digits (state code) + 10 alphanumeric (PAN) + 1 digit (entity number) + 1 alphabet (Z) + 1 alphanumeric (checksum)
        gst_pattern = r'^[0-9]{2}[A-Z0-9]{10}[0-9]{1}[A-Z]{1}[A-Z0-9]{1}$'
        
        if not re.match(gst_pattern, self.gst_number):
            frappe.throw(_('Invalid GST Number format. GST Number should be 15 characters long with format: 2 digits (state code) + 10 alphanumeric (PAN) + 1 digit + 1 alphabet + 1 alphanumeric'))
        
        # Check for uniqueness
        existing_client = frappe.db.get_value('Client', 
            {'gst_number': self.gst_number, 'name': ['!=', self.name]}, 
            'name'
        )
        
        if existing_client:
            frappe.throw(_('GST Number {0} already exists for Client {1}').format(self.gst_number, existing_client))
        
        # Validate state code if customer has state information
        if self.customer:
            try:
                customer_doc = frappe.get_doc('Customer', self.customer)
                if hasattr(customer_doc, 'state') and customer_doc.state:
                    # Get state code from GST number (first 2 digits)
                    gst_state_code = self.gst_number[:2]
                    
                    # Validate that it's a valid state code (01-37)
                    try:
                        state_code_int = int(gst_state_code)
                        if not (1 <= state_code_int <= 37):
                            frappe.throw(_('Invalid state code in GST Number. State code should be between 01 and 37'))
                    except ValueError:
                        frappe.throw(_('Invalid state code in GST Number. First two characters should be numeric'))
            except Exception:
                # If customer doesn't exist or has issues, we'll skip state validation
                pass

    def autoname(self):
        self.name = self.hash

    @frappe.whitelist(allow_guest=True)
    def get_context(self, context):
        context.title = self.customer_name
        context.id = self.route_hash
        context.allow_guest_to_view = 1
