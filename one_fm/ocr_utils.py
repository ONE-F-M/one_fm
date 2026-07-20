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
