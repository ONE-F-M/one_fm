# 2026-04-26
import frappe
from one_fm.utils import create_process_task

def execute():
	"""Create the Method and Process Task records for automated DMARC report fetching."""

	method_path = "one_fm.developer.dmarc_processor.fetch_and_process_dmarc_reports"

	create_process_task(
		"Others",
		"DMARC Report",
		"Daily DMARC Report Fetching",
		process_description="Automated fetching of DMARC aggregate reports via IMAP",
		method=method_path,
		frequency="Daily",
		task_type="Routine",
		is_routine_task=1,
		is_automated=1
	)
