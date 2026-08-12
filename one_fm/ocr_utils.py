# Copyright (c) 2024, ONE FM and contributors
# For license information, please see license.txt

"""
OCR Utility Module for Kuwait Civil ID Data Extraction

This module provides functions to extract data from Kuwait Civil IDs using Mindee API.
It handles text extraction, parsing, date format conversion, and validation.
Uses the same Mindee implementation as the magic link module for consistency and accuracy.
"""

import frappe
import re
from frappe import _
from datetime import datetime
from mindee import ClientV2, InferenceParameters, PathInput
import os


def extract_kuwait_civil_id_data(file_path):
	"""
	Extract data from Kuwait Civil ID using Mindee API (specialized document AI)
	
	Args:
		file_path (str): Path to the Civil ID image file
		
	Returns:
		dict: Extracted data containing civil_id_no, expiry_date, birth_date, company_name_arabic
		
	Raises:
		Exception: If OCR processing fails
	"""
	try:
		# Initialize Mindee client with API key from site config
		mindee_client = ClientV2(api_key=frappe.local.conf.mindee_passport_api)
		civil_id_model = frappe.local.conf.civil_id_model_id
		
		# Prepare input document
		civil_input_doc = PathInput(file_path)
		civil_params = InferenceParameters(
			model_id=civil_id_model,
			# Options for better extraction
			rag=None,
			raw_text=None,
			polygon=None,
			confidence=None,
		)
		
		# Perform OCR extraction
		civil_id_response = mindee_client.enqueue_and_get_inference(
			civil_input_doc, civil_params
		)
		
		# Extract fields from response
		civil_id_fields = civil_id_response.inference.result.fields
		
		# Parse the extracted data
		extracted_data = parse_mindee_civil_id_fields(civil_id_fields)
		
		return extracted_data
		
	except Exception as e:
		frappe.log_error(message=f"Mindee OCR Extraction Failed: {str(e)}", title="Civil ID OCR Error")
		raise Exception("OCR failed to read the document clearly.")


def parse_mindee_civil_id_fields(civil_id_fields):
	"""
	Parse Mindee extracted fields to standard format
	
	Args:
		civil_id_fields (dict): Fields extracted by Mindee API
		
	Returns:
		dict: Parsed data with civil_id_no, expiry_date, birth_date, company_name_arabic
	"""
	data = {
		'civil_id_no': None,
		'expiry_date': None,
		'birth_date': None,
		'company_name_arabic': None
	}
	
	# Extract Civil ID Number
	if hasattr(civil_id_fields, 'civil_id_number') and civil_id_fields.civil_id_number:
		# Mindee may return the value as a float (e.g. 290123456789.0). Simply
		# stripping non-digits is NOT enough: it removes the ".", but the "0" from
		# the ".0" fractional part survives as a trailing digit, producing an extra
		# zero (290123456789 -> 2901234567890). Drop the fractional part first, then
		# strip any remaining separators/spaces so the Civil ID is an exact digit string.
		raw_value = civil_id_fields.civil_id_number.value
		if raw_value not in (None, ""):
			if isinstance(raw_value, float):
				# Convert to int to discard the ".0"; safe as Civil IDs (12 digits)
				# are well within float integer precision.
				raw_str = str(int(raw_value))
			else:
				# String values may still carry a decimal part (e.g. "290123456789.0")
				raw_str = str(raw_value).split(".")[0]
			digits = re.sub(r'[^0-9]', '', raw_str)
			data['civil_id_no'] = digits or None
	
	# Extract Expiry Date
	if hasattr(civil_id_fields, 'expiry_date') and civil_id_fields.expiry_date:
		expiry_value = civil_id_fields.expiry_date.value
		if expiry_value:
			data['expiry_date'] = convert_date_to_frappe_format(expiry_value)
	
	# Extract Birth Date
	if hasattr(civil_id_fields, 'date_of_birth') and civil_id_fields.date_of_birth:
		birth_value = civil_id_fields.date_of_birth.value
		if birth_value:
			data['birth_date'] = convert_date_to_frappe_format(birth_value)
	
	# Extract Company Name in Arabic (if available in the fields)
	# Note: Mindee may not have a specific field for company name
	# We'll try to get it from available fields
	for field_name, field_value in civil_id_fields.items():
		if contains_arabic(str(field_value)) and len(str(field_value).strip()) > 5:
			if not data['company_name_arabic']:
				data['company_name_arabic'] = str(field_value).strip()
	
	return data


def convert_date_to_frappe_format(date_value):
	"""
	Convert date from Mindee format to Frappe format (YYYY-MM-DD)
	
	Args:
		date_value: Date value from Mindee (could be string or date object)
		
	Returns:
		str: Date string in YYYY-MM-DD format or None if invalid
	"""
	try:
		# If it's already a string in YYYY-MM-DD format
		if isinstance(date_value, str):
			# Try parsing as YYYY-MM-DD
			date_obj = datetime.strptime(date_value, "%Y-%m-%d")
			return date_obj.strftime("%Y-%m-%d")
		# If it's a date object
		elif hasattr(date_value, 'strftime'):
			return date_value.strftime("%Y-%m-%d")
		else:
			return None
	except ValueError:
		try:
			# Try parsing as DD/MM/YYYY
			date_obj = datetime.strptime(str(date_value), "%d/%m/%Y")
			return date_obj.strftime("%Y-%m-%d")
		except ValueError:
			return None


def convert_date_format(date_str):
	"""
	Convert date from DD/MM/YYYY to YYYY-MM-DD format
	
	Args:
		date_str (str): Date string in DD/MM/YYYY format
		
	Returns:
		str: Date string in YYYY-MM-DD format or None if invalid
	"""
	try:
		# Parse DD/MM/YYYY
		date_obj = datetime.strptime(date_str, "%d/%m/%Y")
		# Return in YYYY-MM-DD format
		return date_obj.strftime("%Y-%m-%d")
	except ValueError:
		return None


def validate_civil_id_number(civil_id):
	"""
	Validate Civil ID number format (12 digits)
	
	Args:
		civil_id (str): Civil ID number to validate
		
	Returns:
		bool: True if valid, False otherwise
	"""
	if not civil_id:
		return False
	
	# Remove any spaces or dashes
	civil_id_clean = re.sub(r'[^0-9]', '', str(civil_id))
	
	# Check if it's exactly 12 digits
	return len(civil_id_clean) == 12 and civil_id_clean.isdigit()


def contains_arabic(text):
	"""
	Check if text contains Arabic characters
	
	Args:
		text (str): Text to check
		
	Returns:
		bool: True if contains Arabic, False otherwise
	"""
	if not text:
		return False
	arabic_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+')
	return bool(arabic_pattern.search(str(text)))


def extract_arabic_company_name(ocr_text):
	"""
	Extract company name in Arabic from OCR text
	
	Args:
		ocr_text (str): Raw OCR text
		
	Returns:
		str: Extracted Arabic company name or None
	"""
	if not ocr_text:
		return None
		
	lines = str(ocr_text).split('\n')
	
	for line in lines:
		if contains_arabic(line) and len(line.strip()) > 5:
			# Return the first substantial Arabic text found
			return line.strip()
	
	return None


def compare_arabic_names(name1, name2):
	"""
	Compare two Arabic names for similarity
	
	Args:
		name1 (str): First name
		name2 (str): Second name
		
	Returns:
		bool: True if names match (case-insensitive, whitespace-normalized)
	"""
	if not name1 or not name2:
		return False
	
	# Normalize: remove extra whitespace, convert to lowercase
	name1_normalized = ' '.join(str(name1).strip().split())
	name2_normalized = ' '.join(str(name2).strip().split())
	
	return name1_normalized == name2_normalized


# ── Visa Request documents (WI-001977) ────────────────────────────────────────
#
# Two more Mindee models, each with its own id in site_config beside the Civil ID's:
# the e-visa copy and the payment receipt the GRD Operator attaches once a visa is
# issued. The mapping is the work item's own table - Mindee's field name on the left,
# the Visa Request field it fills on the right.
#
# Carrier key, not a Frappe field: the receipt's clock time rides through the mapping
# under this name and is folded into payment_date afterwards.
_PAYMENT_TIME = "_payment_time"
EVISA_FIELD_MAP = {
	# The visa carries two numbers and they are not the same: the Visa Number at the
	# top (رقم التأشيرة) and the Reference below it (رقم المرجع). Review settled on
	# the Visa Number, and the model now returns it under visa_number.
	"visa_number": "visa_reference_number",
	"date_of_issue": "visa_issue_date",
	"date_of_expiry": "visa_expiry_date",
}

RECEIPT_FIELD_MAP = {
	"date": "payment_date",
	# The receipt gives the clock time separately. It is not a field of its own on the
	# Visa Request - it is merged into Payment Date below, which records both.
	"time": _PAYMENT_TIME,
}

# Which of the mapped values are dates, and so go through the Frappe format conversion.
_DATE_TARGETS = {"visa_issue_date", "visa_expiry_date", "payment_date"}


def extract_evisa_data(file_path):
	"""Read an e-visa copy through Mindee (WI-001977).

	Returns {visa_reference_number, visa_issue_date, visa_expiry_date}, with a key
	absent when the model did not find it - a partly-read visa is still worth
	presenting for review, which is what the AC asks for.
	"""
	return _extract_mapped_fields(file_path, "e-visa_model_id", EVISA_FIELD_MAP, "E-Visa")


def extract_payment_receipt_data(file_path):
	"""Read a payment receipt through Mindee (WI-001977). Returns {payment_date}.

	The receipt states the date and the clock time separately; Payment Date records
	both, so two payments made on one day can be told apart by their receipts.
	"""
	return _merge_payment_time(
		_extract_mapped_fields(file_path, "receipt_model_id", RECEIPT_FIELD_MAP, "Payment Receipt")
	)


def _merge_payment_time(extracted):
	"""Fold the receipt's clock time into payment_date and drop the carrier key.

	A receipt with no time still yields a usable Payment Date - it just lands at
	midnight, which is what a Datetime field does with a bare date anyway.
	"""
	clock = extracted.pop(_PAYMENT_TIME, None)
	if clock and extracted.get("payment_date"):
		extracted["payment_date"] = f"{extracted['payment_date']} {clock}"
	return extracted


def _extract_mapped_fields(file_path, model_conf_key, field_map, label):
	"""Run one Mindee model over a file and map its fields onto Frappe fieldnames.

	Shares the Civil ID's client and call shape; only the model and the mapping differ.
	Raises when the model is not configured, rather than quietly returning nothing:
	a missing model id is a deployment problem and should read as one.
	"""
	model_id = frappe.local.conf.get(model_conf_key)
	if not model_id:
		frappe.throw(
			_("No Mindee model configured for {0}. Add {1} to site_config.json.").format(
				label, model_conf_key
			)
		)

	try:
		mindee_client = ClientV2(api_key=frappe.local.conf.mindee_passport_api)
		response = mindee_client.enqueue_and_get_inference(
			PathInput(file_path),
			InferenceParameters(
				model_id=model_id, rag=None, raw_text=None, polygon=None, confidence=None
			),
		)
		return parse_mindee_mapped_fields(response.inference.result.fields, field_map)

	except Exception as e:
		frappe.log_error(
			message=f"Mindee OCR Extraction Failed ({label}): {str(e)}",
			title=f"{label} OCR Error",
		)
		raise Exception(f"OCR failed to read the {label} clearly.")


def parse_mindee_mapped_fields(fields, field_map):
	"""Pull the mapped fields out of a Mindee result.

	Kept separate from the API call so it can be tested against a saved response - the
	sample the work item shipped is what the mapping was written from.

	Values arrive as objects carrying ``.value``; a dict is accepted too so a raw JSON
	response can be passed straight in. A reference number comes back as a number, and
	the target is a Data field, so it is cast - via int() first, or a float would leave
	a ".0" on the end.
	"""
	extracted = {}

	for source_name, target_field in field_map.items():
		field = fields.get(source_name) if isinstance(fields, dict) else getattr(fields, source_name, None)
		if field is None:
			continue

		value = field.get("value") if isinstance(field, dict) else getattr(field, "value", None)
		if value in (None, ""):
			continue

		if target_field in _DATE_TARGETS:
			value = convert_date_to_frappe_format(value)
		elif isinstance(value, float):
			value = str(int(value))
		else:
			value = str(value)

		if value:
			extracted[target_field] = value

	return extracted
