# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Tests for the Transportation Manifest page payload (WI-001766).

The manifest identifies the assigned bus as "<plate>, <model>" so a driver or
field supervisor does not have to look up the vehicle master on site. The string
itself is composed in the page's `vehicleString` helper; what is guarded here is
that the model actually reaches the frontend, since a dropped field would leave
the helper silently rendering the plate alone.
"""

import re

import frappe
from frappe.tests.utils import FrappeTestCase

PAGE_JS = ("one_fm", "one_fm", "page", "transportation_manifest_page", "transportation_manifest_page.js")
BACKEND_PY = (
	"one_fm", "one_fm", "page", "transportation_schedule", "transportation_schedule.py",
)


def _read(parts):
	return frappe.read_file(frappe.get_app_path(*parts))


class TestManifestVehicleString(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.js = _read(PAGE_JS)
		cls.py = _read(BACKEND_PY)

	def test_model_is_a_real_vehicle_field(self):
		# The whole feature rests on this fieldname; ERPNext renaming it would
		# otherwise surface as a blank model rather than an error.
		self.assertTrue(frappe.get_meta("Vehicle").has_field("model"))

	def test_the_backend_fetches_the_model(self):
		# Vehicle metadata for the manifest is batch-fetched once; the model has to
		# be in that field list or vehicleMeta never carries it. The list spans
		# several lines, hence the inline DOTALL.
		self.assertRegex(
			self.py, r'(?s)fields=\[\s*"name",\s*"license_plate".*?"model".*?\]',
		)

	def test_the_model_is_published_in_vehicle_meta(self):
		self.assertIn('"model": v_doc.get("model", "")', self.py)

	def test_the_page_composes_plate_and_model(self):
		self.assertIn("function vehicleString(meta)", self.js)
		self.assertIn("[meta.license_plate, meta.model]", self.js)

	def test_blank_parts_are_filtered_so_no_orphaned_comma(self):
		helper = re.search(r"function vehicleString\(meta\) \{.*?\n\t\}", self.js, re.S)
		self.assertIsNotNone(helper, msg="vehicleString helper not found")
		self.assertIn(".filter(Boolean)", helper.group(0))
		self.assertIn('.join(", ")', helper.group(0))

	def test_both_render_points_show_the_composed_string(self):
		# The AC asks for it in the header strip and in the vehicle detail block.
		self.assertIn('<span class="mfst-tab-plate">${escHtml(vstr)}</span>', self.js)
		self.assertIn('<div class="mfst-vehicle-plate">${escHtml(vstr)}</div>', self.js)

	def test_the_plate_is_no_longer_rendered_on_its_own(self):
		self.assertNotIn("escHtml(meta.license_plate)", self.js)


class TestARunEndsWhenTheBusIsBack(FrappeTestCase):
	"""The Return card is the drive home, not a copy of the last drop-off.

	19/55734 finished its last drop at 07:37 and was shown returning to camp at 07:37 -
	the same minute, with no drive - while its own header said the day ran to 07:57. A
	run leaves before its first stop and is not over until the bus is back, and neither
	of those is a stop.
	"""

	def setUp(self):
		self.page = frappe.read_file(frappe.get_app_path(
			"one_fm", "one_fm", "page", "transportation_manifest_page",
			"transportation_manifest_page.js"
		))
		self.server = frappe.read_file(frappe.get_app_path(
			"one_fm", "one_fm", "page", "transportation_schedule",
			"transportation_schedule.py"
		))

	def test_the_plan_sends_each_run_its_own_legs(self):
		self.assertIn('"tripLegs": trip_legs,', self.server)
		self.assertIn('held["arrival"] = leg.end_time or leg.start_time', self.server)

	def test_the_return_time_is_the_arrival_home(self):
		self.assertIn("const lastTimeISO = legs.arrival", self.page)

	def test_the_departure_is_when_the_bus_leaves_the_camp(self):
		self.assertIn("const firstTimeISO = legs.departure", self.page)

	def test_the_camp_is_the_one_the_run_comes_back_to(self):
		# Not the depot the vehicle is registered at, which is a different fact.
		self.assertIn("const homeCamp = legs.home || legs.camp || accommodation;", self.page)
		self.assertIn("renderReturnCard(lastTimeISO, homeCamp, returningEmployees,", self.page)

	def test_a_run_saved_without_them_still_draws(self):
		# The stops remain the fallback: an older plan has no legs recorded.
		self.assertIn(": new Date(lastTime).toISOString();", self.page)


class TestTheManifestPrintsTheDriversReportTime(FrappeTestCase):
	"""WI-002151, last criterion: an accommodation pickup stop prints the QOA report
	time (Departure - HR QOA minutes) on the manifest, as it does in the modal.

	The only QOA the manifest page knew about was the pass/fail attendance check against
	each rider - a different thing that happens to share the name.
	"""

	def setUp(self):
		self.page = frappe.read_file(frappe.get_app_path(
			"one_fm", "one_fm", "page", "transportation_manifest_page",
			"transportation_manifest_page.js"
		))
		self.server = frappe.read_file(frappe.get_app_path(
			"one_fm", "one_fm", "page", "transportation_schedule",
			"transportation_schedule.py"
		))

	def test_the_plan_sends_the_report_time_with_the_run(self):
		self.assertIn('held["qoa_time"] = str(leg.qoa_time)', self.server)

	def test_the_depart_card_prints_it(self):
		self.assertIn("Driver QOA report time", self.page)
		self.assertIn("qoaTime ?", self.page)

	def test_both_itineraries_pass_it_in(self):
		# A merged run and an ordinary one render through different functions.
		self.assertIn("o.vehicleLabel, true, o.qoaTime", self.page)
		# The camp-by-camp path takes each camp's own report time, and only the first
		# camp falls back to the run's.
		self.assertIn("leg.qoa_time || (index === 0 ? legs.qoa_time : null)", self.page)

	def test_a_run_without_one_prints_nothing(self):
		# AC 1.2: QOA is hidden where it does not apply, not shown empty.
		self.assertIn('qoaTime ? `<div class="mfst-stop-card-shift">', self.page)


class TestTheManifestMarksADayRollover(FrappeTestCase):
	"""AC 1.6: an arrival past midnight is a day later and says so.

	The modal and the details drawer both badge it; the manifest, which is what the
	driver actually reads at 23:50, did not.
	"""

	def setUp(self):
		self.page = frappe.read_file(frappe.get_app_path(
			"one_fm", "one_fm", "page", "transportation_manifest_page",
			"transportation_manifest_page.js"
		))

	def test_the_page_can_measure_the_rollover(self):
		self.assertIn("function dayOffset(fromISO, toISO)", self.page)
		self.assertIn("function rolloverBadge(offset)", self.page)

	def test_a_stop_that_rolls_over_is_badged(self):
		self.assertIn("rolloverBadge(dayOffset(item.runStartISO, stop.time))", self.page)

	def test_the_ride_home_is_badged_too(self):
		# The leg most likely to cross midnight is the one back to the camp.
		self.assertIn("rolloverBadge(dayOffset(runStartISO, time))", self.page)

	def test_it_is_measured_from_when_the_run_left(self):
		self.assertIn("runStartISO: firstTimeISO", self.page)
		self.assertIn("runStartISO: o.firstTimeISO", self.page)


class TestTheManifestReadsAsOneJourney(FrappeTestCase):
	"""Top to bottom, in the order the bus drives it.

	Grouped by camp, a run loading at two camps read as two blocks whose times
	interleaved - Mahboula's 08:37 drop printed above Farwaniya's 08:15 departure. No
	driver can follow that, and it is the same run either way.
	"""

	def setUp(self):
		self.page = frappe.read_file(frappe.get_app_path(
			"one_fm", "one_fm", "page", "transportation_manifest_page",
			"transportation_manifest_page.js"
		))
		self.server = frappe.read_file(frappe.get_app_path(
			"one_fm", "one_fm", "page", "transportation_schedule",
			"transportation_schedule.py"
		))

	def test_the_plan_sends_the_camps_in_the_order_they_are_loaded(self):
		self.assertIn('held.setdefault("camps_ordered", []).append({', self.server)
		self.assertIn('camp["stop_index"]', self.server)

	def test_each_camp_departs_at_its_own_time(self):
		self.assertIn("const leg = campLegs[index] || {};", self.page)
		self.assertIn("html += renderDepartCard(departAt, cg,", self.page)

	def test_each_camp_reports_its_own_driver_time(self):
		self.assertIn("leg.qoa_time || (index === 0 ? legs.qoa_time : null)", self.page)

	def test_the_stops_follow_in_the_order_the_bus_reaches_them(self):
		self.assertIn("new Date(a.stop.time) - new Date(b.stop.time)", self.page)

	def test_the_camp_by_camp_nesting_is_gone(self):
		# It listed a camp's drops under it, so the two blocks' clocks interleaved.
		self.assertNotIn("dropByCamp", self.page)

	def test_the_drive_home_runs_from_the_last_stop_reached(self):
		self.assertIn("renderTransit(calcTransit(prevTime, lastTimeISO))", self.page)
