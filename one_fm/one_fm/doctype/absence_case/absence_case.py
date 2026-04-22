import frappe
from frappe import throw, _
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime, flt
from frappe.model.mapper import get_mapped_doc


class AbsenceCase(Document):
	def validate(self):
		self.validate_formal_hearing_datetime()

	def validate_formal_hearing_datetime(self):
		if not self.formal_hearing_start_datetime:
			return

		# 24-hour notice validation
		now = now_datetime()
		start_datetime = get_datetime(self.formal_hearing_start_datetime)

		# Calculate difference in hours
		diff = (start_datetime - now).total_seconds() / 3600

		if diff < 24:
			throw(_("Formal Hearing Notice must be at least 24 hours prior."))

		# End date validation
		if self.formal_hearing_end_datetime:
			end_datetime = get_datetime(self.formal_hearing_end_datetime)
			if end_datetime <= start_datetime:
				throw(_("Formal Hearing End Datetime must be after Start Datetime."))


@frappe.whitelist()
def make_formal_hearing(source_name: str):
	def postprocess(source, target):
		# Convert Select (Yes/No) to Check (1/0)
		target.received_leave_extension_request = 1 if source.received_leave_extension_request == "Yes" else 0
		
		# Set link back to absence case
		target.absence_case = source.name

	doc = get_mapped_doc("Absence Case", source_name, {
		"Absence Case": {
			"doctype": "Formal Hearing",
			"field_map": {
				"location_status": "location_status",
				"absence_reason_details": "absence_reason_details",
				"leave_application": "leave_application"
			}
		}
	}, target_doc=None, postprocess=postprocess)

	return doc
