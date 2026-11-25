# Copyright (c) 2023, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from one_fm.ocr_utils import (
	extract_kuwait_civil_id_data,
	validate_civil_id_number,
	compare_arabic_names
)
import os


class SubcontractStaffShortlistDetail(Document):
	def validate(self):
		"""Validate Civil ID number format and dates"""
		if self.id_type == "Civil ID" and self.civil_id_no:
			if not validate_civil_id_number(self.civil_id_no):
				frappe.throw(_("Civil ID No must be exactly 12 digits"))


def get_ocr_file_path(file_url):
	"""Disk path of a File at file_url that the caller can read; refuses paths outside the site's files folders."""
	file_names = frappe.get_all("File", filters={"file_url": file_url}, pluck="name")
	if not file_names:
		return None
	if not any(frappe.has_permission("File", "read", doc=name) for name in file_names):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	file_path = os.path.realpath(frappe.get_doc("File", file_names[0]).get_full_path())
	folders = [os.path.realpath(frappe.get_site_path(*parts)) for parts in (("public", "files"), ("private", "files"))]
	if not any(os.path.commonpath((folder, file_path)) == folder for folder in folders):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	return file_path


@frappe.whitelist()
def trigger_ocr(file_url: str, id_type: str, subcontractor: str | None = None):
	"""
	Trigger OCR processing for uploaded Civil ID document
	
	Args:
		file_url (str): URL of the uploaded file
		id_type (str): Type of ID (must be 'Civil ID')
		subcontractor (str): ID of the subcontractor (optional)
		
	Returns:
		dict: Extracted data or error message
	"""
	# Only process if ID Type is Civil ID
	if id_type != "Civil ID":
		return {
			"success": False,
			"message": "OCR is only triggered for Civil ID type"
		}

	file_path = get_ocr_file_path(file_url)
	if not file_path or not os.path.exists(file_path):
		return {
			"success": False,
			"message": "File not found",
			"url": file_url
		}

	try:
		# Extract data using OCR
		extracted_data = extract_kuwait_civil_id_data(file_path)
		
		# Validate extracted data
		if not extracted_data.get('civil_id_no'):
			return {
				"success": False,
				"message": "OCR failed to read the document clearly."
			}
		
		# Check if subcontractor name in Arabic exists
		subcontractor_name_arabic = None
		if subcontractor:
			# Get from Supplier doctype
			subcontractor_name_arabic = frappe.db.get_value(
				"Supplier", 
				subcontractor, 
				"supplier_name_in_arabic"
			)
		
		# Prepare warnings
		warnings = []
		
		# Compare company names if both exist
		if extracted_data.get('company_name_arabic') and subcontractor_name_arabic:
			if not compare_arabic_names(extracted_data['company_name_arabic'], subcontractor_name_arabic):
				warnings.append("Subcontractor Name in Arabic not matching with the Staff Civil ID.")
		elif extracted_data.get('company_name_arabic') and not subcontractor_name_arabic and subcontractor:
			warnings.append("Comparison failed: Subcontractor Name in Arabic is missing in the main form. Please update the Subcontractor record first.")
		
		return {
			"success": True,
			"data": {
				"civil_id_no": extracted_data.get('civil_id_no'),
				"civil_id_expiry_date": extracted_data.get('expiry_date'),
				"date_of_birth": extracted_data.get('birth_date')
			},
			"warnings": warnings
		}
		
	except Exception as e:
		frappe.log_error(message=f"OCR Trigger Error: {str(e)}", title="Civil ID OCR")
		return {
			"success": False,
			"message": str(e)
		}
