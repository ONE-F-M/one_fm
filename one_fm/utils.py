# -*- coding: utf-8 -*-
# encoding: utf-8
from __future__ import unicode_literals
import frappe
from frappe import _
import frappe, os
from frappe.model.document import Document
from frappe.utils import get_site_base_path
from frappe.utils.data import flt, nowdate, getdate, cint
from frappe.utils.csvutils import read_csv_content_from_uploaded_file, read_csv_content
from frappe.utils import cint, cstr, flt, nowdate, comma_and, date_diff, getdate


@frappe.whitelist()
def get_item_code(parent_item_group = None ,subitem_group = None ,item_group = None ,cur_item_id = None):
	item_code = None
	if parent_item_group:
		parent_item_group_code = frappe.db.get_value('Item Group', parent_item_group, 'item_group_code')
		item_code = parent_item_group_code

	if subitem_group:
		subitem_group_code = frappe.db.get_value('Item Group', subitem_group, 'item_group_code')
		item_code = parent_item_group_code+subitem_group_code

	if item_group:
		item_group_code = frappe.db.get_value('Item Group', item_group, 'item_group_code')
		item_code = parent_item_group_code+subitem_group_code+item_group_code

	if cur_item_id:
			item_code = parent_item_group_code+subitem_group_code+item_group_code+cur_item_id

	return item_code
