# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the PAM License Details processes run as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one. The other PAM License Details tests read the rules from here
through rules(), and install_scripts() puts these bodies on the site for the hooks to run.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

SCRIPTS = {
	"Recount PAM License": """# Recounts every derived figure on one PAM License Details record: the sector headcounts and
# ratio figures, the licence's total and status, and the quota rows. A licence whose status
# moves also moves on the PAM Files that list it.
# Runs from the PAM License Details map after every save of the licence, and from the
# Employee, Visa Request, Visa Cancellation Request and PAM Designation List hooks for each
# licence they touched. Figures are written with frappe.db.set_value, so no save runs again.
from frappe.query_builder import DocType
from frappe.utils import cint, flt

from one_fm.visa_management.doctype.visa_request.visa_request import cancelled_visa_requests

KUWAITI = "Kuwaiti"

# Expatriates PAM allows each occupational sector over what the ratio permits, by sector record name.
SECTOR_EXPAT_ALLOWANCE = {
	"علميون و فنيون": 5,
	"مديرون": 1,
	"كتبة و تنفيذيون": 2,
	"مقدمي خدمات": 10,
	"بائعون": 3,
}
# PAM does not ration this sector: no expatriates are allowed and none are in violation.
EXEMPT_SECTOR = "مهن غير مشمولة بالنسبة"

COMPLIANT = "Compliant"
NON_COMPLIANT = "Non-Compliant"

# Visa Request states that hold a visa against a quota: Pending By MOI onwards.
VISA_ISSUED_STATES = (
	"Pending By MOI",
	"Pending Visa Issuance",
	"Pending Recruiter Confirmation",
	"Completed",
	"Awaiting Visa Cancellation",
)

# Claims against a quota's allocation.
QUOTA_DEDUCTIONS = (
	"registered_numbers_of_employees",
	"number_of_visas_issued",
	"number_of_transfer_requests",
)


# A headcount as a whole number, half rounding up.
def to_whole(value):
	return int(flt(value) + 0.5)


# A figure as it goes into a Data field: "3", not "3.0".
def as_figure(value):
	return str(to_whole(value))


# nationals x (100 - ratio) / ratio plus the sector allowance. A blank or zero ratio permits none.
def expats_allowed(sector, ratio, nationals):
	if sector == EXEMPT_SECTOR:
		return 0.0

	ratio = flt(ratio)
	if ratio <= 0:
		return 0.0

	return flt(nationals) * (100 - ratio) / ratio + SECTOR_EXPAT_ALLOWANCE.get(sector, 0)


# The figures one sector row's ratio and headcounts imply. Excess and violation never go below zero.
def derived_figures(sector, ratio, nationals, expatriates):
	ratio = flt(ratio)

	required = 0.0
	if 0 < ratio < 100:
		required = flt(expatriates) * ratio / (100 - ratio)
	required = to_whole(required)

	excess = max(flt(nationals) - required, 0)

	allowed = to_whole(expats_allowed(sector, ratio, nationals))
	violated = 0.0 if sector == EXEMPT_SECTOR else max(flt(expatriates) - allowed, 0)

	return {
		"required_number_of_national_workers": as_figure(required),
		"exceeding_the_ratio_number_of_national_workers": as_figure(excess),
		"exempt_number_of_workers": as_figure(allowed),
		"violation_number_of_workers": as_figure(violated),
		"status": NON_COMPLIANT if violated > 0 else COMPLIANT,
	}


# Nationals and expatriates on the licence in this sector, counting only the company's residency.
def count_workers(license_name, sector):
	Employee = DocType("Employee")
	Designation = DocType("PAM Designation List")

	rows = (
		frappe.qb.from_(Employee)
		.join(Designation)
		.on(Employee.one_fm_pam_designation == Designation.name)
		.select(Employee.one_fm_nationality, frappe.qb.terms.Function("Count", Employee.name).as_("count"))
		.where(Employee.pam_file == license_name)
		.where(Employee.under_company_residency == 1)
		.where(Designation.occupational_sector == sector)
		.groupby(Employee.one_fm_nationality)
	).run(as_dict=True)

	nationals = sum(row["count"] for row in rows if row["one_fm_nationality"] == KUWAITI)
	expatriates = sum(row["count"] for row in rows if row["one_fm_nationality"] != KUWAITI)

	return nationals, expatriates


# Sectors that hold at least one of this licence's employees.
def employee_sectors(license_name):
	Employee = DocType("Employee")
	Designation = DocType("PAM Designation List")

	rows = (
		frappe.qb.from_(Employee)
		.join(Designation)
		.on(Employee.one_fm_pam_designation == Designation.name)
		.select(Designation.occupational_sector)
		.distinct()
		.where(Employee.pam_file == license_name)
		.where(Employee.under_company_residency == 1)
		.where(Designation.occupational_sector.isnotnull())
		.where(Designation.occupational_sector != "")
	).run(as_dict=True)

	return [row["occupational_sector"] for row in rows]


# A sector row for a sector the licence has no row for. The ratio is left for the operator.
def add_sector_row(license_name, sector):
	row = frappe.get_doc({
		"doctype": "PAM License Stats",
		"name": frappe.generate_hash(length=10),
		"parenttype": "PAM License Details",
		"parentfield": "pam_license_stats",
		"parent": license_name,
		"occupational_sector": sector,
		"idx": frappe.db.count(
			"PAM License Stats", {"parent": license_name, "parentfield": "pam_license_stats"}
		) + 1,
	})
	row.db_insert()
	return frappe._dict({"name": row.name, "ratio_number_of_national_workers": None})


# Write one sector row's headcounts and the figures derived from them. A missing row is
# added only when somebody is counted in it.
def recount_sector(license_name, sector):
	if not license_name or not frappe.db.exists("PAM License Details", license_name):
		return

	nationals, expatriates = count_workers(license_name, sector)

	row = frappe.db.get_value(
		"PAM License Stats",
		{
			"parent": license_name,
			"parenttype": "PAM License Details",
			"parentfield": "pam_license_stats",
			"occupational_sector": sector,
		},
		["name", "ratio_number_of_national_workers"],
		as_dict=True,
	)
	if not row:
		if not (nationals or expatriates):
			return
		row = add_sector_row(license_name, sector)

	figures = {
		"national_number_of_workers": str(nationals),
		"expatriate_number_of_workers": str(expatriates),
	}
	figures.update(
		derived_figures(sector, row.ratio_number_of_national_workers, nationals, expatriates)
	)
	frappe.db.set_value("PAM License Stats", row.name, figures, update_modified=False)


# Everyone on the licence under the company's residency, by the pam_file link.
def count_license_employees(license_name):
	if not license_name:
		return 0

	return frappe.db.count("Employee", {"pam_file": license_name, "under_company_residency": 1})


# Active with employees, Inactive with none. Suspended is set by hand and kept.
def license_status(total, current):
	if current == "Suspended":
		return current
	return "Active" if cint(total) > 0 else "Inactive"


# Copy the licence's status onto the PAM File rows that list it, and recount those files.
def refresh_pam_files(license_name, status):
	rows = frappe.get_all(
		"PAM Licenses",
		filters={
			"parenttype": "PAM File",
			"civil_id_number_for_licensing": license_name,
			"status": ["!=", status],
		},
		fields=["name", "parent"],
	)
	for row in rows:
		frappe.db.set_value("PAM Licenses", row.name, "status", status, update_modified=False)

	for parent in dict.fromkeys(row.parent for row in rows):
		pam_file = frappe.get_doc("PAM File", parent)
		pam_file.set_license_counts()
		frappe.db.set_value(
			"PAM File",
			parent,
			{
				"number_of_active_licenses": pam_file.number_of_active_licenses,
				"number_of_inactive_licenses": pam_file.number_of_inactive_licenses,
				"file_status": pam_file.file_status,
			},
			update_modified=False,
		)


# Write the licence's headcount and status, and carry the status to its PAM Files.
def recount_license_total(license_name):
	if not license_name or not frappe.db.exists("PAM License Details", license_name):
		return

	count = count_license_employees(license_name)
	current = frappe.db.get_value("PAM License Details", license_name, "status")
	status = license_status(count, current)
	frappe.db.set_value(
		"PAM License Details",
		license_name,
		{"total_number_of_employees": str(count), "status": status},
		update_modified=False,
	)
	refresh_pam_files(license_name, status)


# Employees on the licence whose designation is in this quota and who are registered,
# meaning they have a work permit expiry date.
def count_quota_employees(license_name, quota_type):
	if not license_name or not quota_type:
		return 0

	Employee = DocType("Employee")
	Designation = DocType("PAM Designation List")

	rows = (
		frappe.qb.from_(Employee)
		.join(Designation)
		.on(Employee.one_fm_pam_designation == Designation.name)
		.select(frappe.qb.terms.Function("Count", Employee.name).as_("count"))
		.where(Employee.pam_file == license_name)
		.where(Employee.under_company_residency == 1)
		.where(Employee.work_permit_expiry_date.isnotnull())
		.where(Designation.quota_type == quota_type)
	).run(as_dict=True)

	return rows[0]["count"] if rows else 0


# The job applicants who have arrived and been registered on the company's residency.
def registered_applicants(job_applicants):
	job_applicants = [applicant for applicant in (job_applicants or []) if applicant]
	if not job_applicants:
		return set()

	return set(
		frappe.get_all(
			"Employee",
			filters=[
				["job_applicant", "in", job_applicants],
				["under_company_residency", "=", 1],
				["work_permit_expiry_date", "is", "set"],
			],
			pluck="job_applicant",
		)
	)


# Visas issued against the licence and not yet cancelled or registered, per quota type.
def visas_issued_by_quota(license_name):
	if not license_name:
		return {}

	requests = frappe.get_all(
		"Visa Request",
		filters=[
			["custom_pam_file", "=", license_name],
			["workflow_state", "in", VISA_ISSUED_STATES],
			["custom_pam_designation_list", "is", "set"],
		],
		fields=["name", "custom_pam_designation_list", "job_applicant"],
	)
	if not requests:
		return {}

	released = cancelled_visa_requests([request["name"] for request in requests])

	# A holder who has arrived and registered is counted in the registered figure instead.
	arrived = registered_applicants([request.get("job_applicant") for request in requests])
	released |= {request["name"] for request in requests if request.get("job_applicant") in arrived}

	designations = {
		request["custom_pam_designation_list"] for request in requests if request["name"] not in released
	}
	if not designations:
		return {}

	quota_of = dict(
		frappe.get_all(
			"PAM Designation List",
			filters={"name": ["in", list(designations)]},
			fields=["name", "quota_type"],
			as_list=True,
		)
	)

	counts = {}
	for request in requests:
		if request["name"] in released:
			continue
		quota_type = quota_of.get(request["custom_pam_designation_list"])
		# A designation with no quota type counts against no row.
		if not quota_type:
			continue
		counts[quota_type] = counts.get(quota_type, 0) + 1

	return counts


# Allocated quota minus everything claimed against it, never below zero. Blanks count as zero.
def available_quota(row):
	allocated = flt(row.get("allocated_quota"))
	claimed = sum(flt(row.get(fieldname)) for fieldname in QUOTA_DEDUCTIONS)

	return as_figure(max(allocated - claimed, 0))


def total_available_quota(rows):
	return as_figure(sum(flt(row.get("available_quota")) for row in rows))


# Write every quota row's registered and issued figures, its remainder, and the licence total.
# A missing quota row is never added: a row is an allocation PAM granted.
def recount_quota_rows(license_name):
	if not license_name or not frappe.db.exists("PAM License Details", license_name):
		return

	counts = {}
	issued = visas_issued_by_quota(license_name)

	rows = frappe.get_all(
		"Quota Classification",
		filters={
			"parent": license_name,
			"parenttype": "PAM License Details",
			"parentfield": "quota_classification",
		},
		fields=["name", "type_of_quota", "allocated_quota", "number_of_transfer_requests"],
	)
	computed_rows = []
	for row in rows:
		quota_type = row["type_of_quota"]
		if quota_type not in counts:
			counts[quota_type] = str(count_quota_employees(license_name, quota_type))

		figures = {
			"registered_numbers_of_employees": counts[quota_type],
			"number_of_visas_issued": str(issued.get(quota_type, 0)),
		}
		figures["available_quota"] = available_quota({**row, **figures})

		frappe.db.set_value("Quota Classification", row["name"], figures, update_modified=False)
		computed_rows.append({"available_quota": figures["available_quota"]})

	frappe.db.set_value(
		"PAM License Details",
		license_name,
		"total_available_quota",
		total_available_quota(computed_rows),
		update_modified=False,
	)


# Every figure on the licence: each configured sector row, any sector its employees are in
# that has no row yet, the total and status, and the quota rows.
def recount_license(license_name):
	if not license_name or not frappe.db.exists("PAM License Details", license_name):
		return

	sectors = frappe.get_all(
		"PAM License Stats",
		filters={"parent": license_name, "parenttype": "PAM License Details", "parentfield": "pam_license_stats"},
		pluck="occupational_sector",
	)
	for sector in dict.fromkeys([s for s in sectors if s] + employee_sectors(license_name)):
		recount_sector(license_name, sector)

	recount_license_total(license_name)
	recount_quota_rows(license_name)


# The map passes the licence as doc. Run with an empty doc, it only defines the functions above.
if doc and doc.get("name"):
	recount_license(doc.name)
	result["recounted"] = doc.name
""",
	"Find Expiring Letters of Guarantee": """# Daily: the PAM licences whose letter of guarantee expires in exactly 7 days.
# An exact date, so each licence is announced once. Only a licence with LG Details ticked has an LG.
licenses = frappe.get_all(
	"PAM License Details",
	filters={"lg_details_applicable": 1, "lg_expiry_date": frappe.utils.add_days(frappe.utils.today(), 7)},
	pluck="name",
)

result["licenses"] = licenses
result["records_found"] = bool(licenses)
""",
	"Send LG Expiry Notices": """# One email per licence found by Find Expiring Letters of Guarantee. The recipients are the
# LG Expiry Notification Recipients in GRD Settings: the first row is addressed, the rest are
# copied in. Everyone told also gets the notice on the bell.
from one_fm.processor import sendemail

NOTICE_DAYS = 7

users = []
for user in frappe.get_all(
	"Action User",
	filters={"parenttype": "GRD Settings", "parentfield": "lg_expiry_notification_recipients"},
	pluck="user",
	order_by="idx asc",
):
	# Administrator is nobody's mailbox, and sendemail strips it from recipients but not from cc.
	if user and user != "Administrator" and user not in users:
		users.append(user)

licenses = task_data.get("licenses") or []
result["notices_sent"] = 0

if licenses and not users:
	frappe.log_error(
		title="LG Expiry Notification",
		message="{0} licence(s) have a letter of guarantee expiring in {1} days, but no recipients are configured in GRD Settings.".format(len(licenses), NOTICE_DAYS),
	)

for name in licenses if users else []:
	# One licence that cannot be sent is logged and the rest still go: a throw would halt the process.
	try:
		license = frappe.db.get_value(
			"PAM License Details", name,
			["name", "lg_number", "lg_expiry_date", "license_name", "civil_id_number_for_licensing", "issuing_authority"],
			as_dict=True,
		)
		subject = "LG Expiry Warning: {0}".format(license.lg_number or license.name)
		message = frappe.render_template("one_fm/templates/emails/lg_expiry_notification.html", {
			"lg_number": license.lg_number or "",
			"lg_expiry_date": frappe.utils.formatdate(license.lg_expiry_date),
			"license_name": license.license_name or license.name,
			"civil_id_number_for_licensing": license.civil_id_number_for_licensing or "",
			"issuing_authority": license.issuing_authority or "",
			"license_link": frappe.utils.get_url_to_form("PAM License Details", license.name),
			"days_left": NOTICE_DAYS,
		})

		for user in users:
			# "Alert" is the one type Frappe never emails, so the bell entry does not send a second copy.
			frappe.get_doc({
				"doctype": "Notification Log", "type": "Alert", "subject": subject, "email_content": message,
				"document_type": "PAM License Details", "document_name": license.name, "for_user": user,
			}).insert()

		# expose_recipients="header" writes the real To and Cc headers instead of one personal copy each.
		sendemail(
			recipients=[users[0]], cc=users[1:] or None, subject=subject, content=message,
			reference_doctype="PAM License Details", reference_name=license.name,
			expose_recipients="header", is_scheduler_email=True,
		)
		result["notices_sent"] += 1
	except Exception:
		frappe.log_error(title="LG Expiry Notification: {0}".format(name), message=frappe.get_traceback())
""",
}


def run(script_name, doc=None, **task_data):
	"""Run a script the way the Processa engine does and return its result."""
	result = {}
	namespace = {
		"frappe": frappe,
		"doc": doc or frappe._dict(),
		"task_data": task_data,
		"result": result,
		"context_doctype": doc.doctype if doc else "",
		"context_docname": doc.name if doc else "",
	}
	exec(SCRIPTS[script_name], namespace)
	return result


def rules():
	"""The Recount PAM License functions and constants, without recounting anything.

	A fresh namespace each call. The functions look each other up in it, so a test can
	replace one by assigning into the returned dict.
	"""
	namespace = {"frappe": frappe, "doc": frappe._dict(), "task_data": {}, "result": {},
		"context_doctype": "", "context_docname": ""}
	exec(SCRIPTS["Recount PAM License"], namespace)
	return namespace


def install_scripts():
	"""Put these bodies on the site, so the hooks under test run the reviewed scripts."""
	for name, body in SCRIPTS.items():
		if frappe.db.exists("Server Script", name):
			frappe.db.set_value("Server Script", name, "script", body, update_modified=False)
		else:
			frappe.get_doc({"doctype": "Server Script", "name": name, "script_type": "API",
				"api_method": frappe.scrub(name), "script": body}).db_insert()


class TestSiteScripts(FrappeTestCase):
	def test_site_scripts_match_this_file(self):
		for name, body in SCRIPTS.items():
			saved = frappe.db.get_value("Server Script", name, "script")
			if saved is None:
				continue
			self.assertEqual(saved.strip(), body.strip(), name)


SEEDED = "PAM-LG-TEST-"
SETTINGS = "GRD Settings"
RECIPIENTS_FIELD = "lg_expiry_notification_recipients"
NOTICE_DAYS = 7


def _clear():
	# Rollback is per class, so each test clears what the one before it sent.
	frappe.db.delete("Notification Log", {"document_name": ["like", SEEDED + "%"]})
	frappe.db.delete("PAM License Details", {"name": ["like", SEEDED + "%"]})
	frappe.db.delete("Action User", {"parenttype": SETTINGS, "parentfield": RECIPIENTS_FIELD})


def _licence(suffix, lg_expiry_date, lg_number="LG-001", lg_details_applicable=1):
	"""A licence written without the map: the recount is not under test here."""
	doc = frappe.new_doc("PAM License Details")
	doc.name = SEEDED + suffix
	doc.label_name = SEEDED + suffix
	doc.license_name = "LG Test Licence"
	doc.civil_id_number_for_licensing = "999" + suffix
	doc.issuing_authority = "PAM"
	doc.lg_details_applicable = lg_details_applicable
	doc.lg_number = lg_number
	doc.lg_expiry_date = lg_expiry_date
	doc.db_insert()
	return doc.name


def _set_recipients(users):
	frappe.db.delete("Action User", {"parenttype": SETTINGS, "parentfield": RECIPIENTS_FIELD})
	for idx, user in enumerate(users, 1):
		row = frappe.new_doc("Action User")
		row.parent = SETTINGS
		row.parenttype = SETTINGS
		row.parentfield = RECIPIENTS_FIELD
		row.idx = idx
		row.user = user
		row.db_insert()


def _real_users(count):
	users = frappe.get_all(
		"User",
		filters={"enabled": 1, "name": ["not in", ["Administrator", "Guest"]]},
		pluck="name",
		limit=count,
	)
	return users if len(users) == count else None


def _found():
	return run("Find Expiring Letters of Guarantee")["licenses"]


def _send(licenses):
	"""Run the send script with sendemail captured; returns (result, calls)."""
	calls = []
	with patch("one_fm.processor.sendemail", lambda **kwargs: calls.append(kwargs)):
		result = run("Send LG Expiry Notices", licenses=licenses)
	return result, calls


class TestWhichLicencesAreFound(FrappeTestCase):
	def setUp(self):
		_clear()
		self.addCleanup(_clear)
		self.due = add_days(today(), NOTICE_DAYS)

	def test_a_licence_expiring_in_a_week_is_found(self):
		name = _licence("A", self.due)
		self.assertIn(name, _found())
		self.assertTrue(run("Find Expiring Letters of Guarantee")["records_found"])

	def test_a_day_either_side_is_not(self):
		_licence("B", add_days(today(), NOTICE_DAYS - 1))
		_licence("C", add_days(today(), NOTICE_DAYS + 1))
		self.assertFalse({SEEDED + "B", SEEDED + "C"} & set(_found()))

	def test_a_licence_with_no_expiry_date_is_not_found(self):
		_licence("D", None)
		self.assertNotIn(SEEDED + "D", _found())

	def test_an_unticked_licence_is_not_found(self):
		_licence("OFF", self.due, lg_number="LG-STALE", lg_details_applicable=0)
		self.assertNotIn(SEEDED + "OFF", _found())

	def test_nothing_due_sends_the_map_down_the_no_branch(self):
		frappe.db.set_value("PAM License Details", {"lg_expiry_date": self.due}, "lg_expiry_date", None)
		self.assertEqual(run("Find Expiring Letters of Guarantee"), {"licenses": [], "records_found": False})


class TestWhoIsTold(FrappeTestCase):
	def setUp(self):
		_clear()
		self.addCleanup(_clear)
		self.name = _licence("T", add_days(today(), NOTICE_DAYS), lg_number="LG-PAM-TEST")

	def test_nobody_configured_sends_nothing_and_logs_why(self):
		before = frappe.db.count("Error Log", {"method": "LG Expiry Notification"})
		result, calls = _send([self.name])
		self.assertEqual((result["notices_sent"], calls), (0, []))
		self.assertEqual(frappe.db.count("Error Log", {"method": "LG Expiry Notification"}), before + 1)

	def test_the_first_row_is_addressed_and_the_rest_are_copied(self):
		users = _real_users(3)
		if not users:
			self.skipTest("needs three enabled users on this site")
		_set_recipients(list(reversed(users)))

		_result, calls = _send([self.name])

		self.assertEqual(calls[0]["recipients"], [users[2]])
		self.assertEqual(calls[0]["cc"], [users[1], users[0]])

	def test_administrator_and_repeats_are_dropped(self):
		users = _real_users(2)
		if not users:
			self.skipTest("needs two enabled users on this site")
		_set_recipients(["Administrator", users[0], users[1], users[0]])

		_result, calls = _send([self.name])

		self.assertEqual((calls[0]["recipients"], calls[0]["cc"]), ([users[0]], [users[1]]))


class TestTheAlertItself(FrappeTestCase):
	def setUp(self):
		_clear()
		self.addCleanup(_clear)
		self.users = _real_users(2)
		if not self.users:
			self.skipTest("needs two enabled users on this site")
		_set_recipients(self.users)
		self.name = _licence("F", add_days(today(), NOTICE_DAYS), lg_number="LG-PAM-TEST")
		self.result, calls = _send([self.name])
		self.call = calls[0]
		self.assertEqual(len(calls), 1)

	def test_one_email_tied_back_to_the_licence(self):
		self.assertEqual(self.result["notices_sent"], 1)
		self.assertEqual(self.call["reference_doctype"], "PAM License Details")
		self.assertEqual(self.call["reference_name"], self.name)
		self.assertIn("LG-PAM-TEST", self.call["subject"])

	def test_the_body_prints_the_lg_and_follows_the_assignment_rule_layout(self):
		content = self.call["content"]
		for text in ("LG-PAM-TEST", "LG Number", "LG Expiry Date", "requires your attention/action",
				'<table cellpadding="0" cellspacing="0" border="1" style="border-collapse: collapse;">'):
			self.assertIn(text, content)

	def test_the_copy_is_written_as_a_real_cc_header(self):
		self.assertEqual(self.call["expose_recipients"], "header")

	def test_everyone_told_gets_it_on_the_bell_and_no_second_email(self):
		logs = frappe.get_all(
			"Notification Log",
			filters={"document_type": "PAM License Details", "document_name": self.name},
			fields=["for_user", "type"],
		)
		self.assertEqual(sorted(log.for_user for log in logs), sorted(self.users))
		self.assertEqual({log.type for log in logs}, {"Alert"})

	def test_alert_is_still_the_type_frappe_never_emails(self):
		from frappe.desk.doctype.notification_settings.notification_settings import (
			is_email_notifications_enabled_for_type,
		)

		self.assertFalse(is_email_notifications_enabled_for_type(self.users[0], "Alert"))

	def test_one_failing_licence_does_not_stop_the_rest(self):
		other = _licence("G", add_days(today(), NOTICE_DAYS), lg_number="LG-PAM-OTHER")
		result, calls = _send(["missing-licence", other])
		self.assertEqual(result["notices_sent"], 1)
		self.assertEqual(calls[0]["reference_name"], other)


class TestTheSettingsAndTheBox(FrappeTestCase):
	def test_grd_settings_carries_the_recipient_table(self):
		field = frappe.get_meta(SETTINGS).get_field(RECIPIENTS_FIELD)
		self.assertIsNotNone(field, "run bench migrate")
		self.assertEqual((field.fieldtype, field.options), ("Table MultiSelect", "Action User"))

	def test_the_daily_job_is_gone(self):
		from one_fm import hooks

		self.assertNotIn("one_fm.grd.lg_expiry.notify_lg_expiry", hooks.scheduler_events["daily"])

	def test_the_lg_fields_are_hidden_until_the_box_is_ticked(self):
		meta = frappe.get_meta("PAM License Details")
		self.assertEqual(meta.get_field("lg_details_applicable").fieldtype, "Check")
		self.assertFalse(frappe.utils.cint(meta.get_field("lg_details_applicable").default))
		for fieldname in ("lg_number", "lg_expiry_date"):
			self.assertEqual(meta.get_field(fieldname).depends_on, "eval:doc.lg_details_applicable", fieldname)


class TestRecountThroughTheSite(FrappeTestCase):
	"""The hooks and the map both run the site's Recount PAM License script."""

	def setUp(self):
		install_scripts()

	def test_recount_runs_the_site_script(self):
		from one_fm.grd.doctype.pam_license_details.pam_license_details import recount

		name = frappe.db.get_value("PAM License Details", {}, "name")
		if not name:
			self.skipTest("needs a PAM License Details record")
		frappe.db.set_value("PAM License Details", name, "total_available_quota", "", update_modified=False)

		recount(name)

		self.assertNotEqual(frappe.db.get_value("PAM License Details", name, "total_available_quota"), "")

	def test_a_missing_script_is_logged_not_raised(self):
		from one_fm.grd.doctype.pam_license_details.pam_license_details import RECOUNT_SCRIPT, recount

		name = frappe.db.get_value("PAM License Details", {}, "name")
		if not name:
			self.skipTest("needs a PAM License Details record")
		frappe.db.delete("Server Script", RECOUNT_SCRIPT)
		before = frappe.db.count("Error Log", {"method": "PAM License recount skipped"})

		recount(name)

		self.assertEqual(frappe.db.count("Error Log", {"method": "PAM License recount skipped"}), before + 1)

	def test_run_from_the_map_recounts_the_licence_it_is_given(self):
		name = frappe.db.get_value("PAM License Details", {}, "name")
		if not name:
			self.skipTest("needs a PAM License Details record")
		self.assertEqual(run("Recount PAM License", frappe.get_doc("PAM License Details", name)), {"recounted": name})

	def test_without_a_licence_it_only_defines_the_rules(self):
		self.assertEqual(run("Recount PAM License"), {})
