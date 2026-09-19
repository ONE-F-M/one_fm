# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002544: the manifest's vehicle tabs, and a delete that stranded them.

**AC1 was a real ordering bug.** The Schedule lists vehicles by ``Vehicle.name`` -
``build_vehicle_list`` passes ``order_by="name asc"``. The manifest built its tab order
from the assignment rows instead, taking each vehicle the first time it appeared, which
is whatever order the canvas happened to save its rows in. The same fleet was listed one
way on the board and another on the driver's page, so a supervisor comparing the two had
to hunt for a vehicle rather than find it in the same place. Sorting the vehicle order
makes both screens read from the same rule.

Verified on the live board, 25 vehicles: ``VHL-L-0004 ... VHL-S-0013``, name order on
both screens; ``VHL-S-000`` narrows to five tabs, the driver fragment "gani" to one, and
a filtered tab is still selectable; the arrows scroll 0 -> 965 -> 0 with the badge moving
"17 more" -> "4 5 more | 11 more" and back.

**A latent bug surfaced while testing.** ``_prune_stale`` deletes with ``force=True``,
which skips link validation - so pruning a card left every manifest row that referenced
it pointing at a document that no longer exists. From then on the manifest could not be
SAVED at all: ``get_manifest_data_for_plan`` throws LinkValidationError, which reaches
the driver's page as a 417 and a blank screen. 13 rows across 13 manifests, going back to
30-08, were in that state on this bench. The prune now releases the reference first.
"""

import inspect
import pathlib

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.transportation_shipment import shipment_generator
from one_fm.one_fm.page.transportation_schedule import transportation_schedule

SHEET = pathlib.Path(frappe.get_app_path(
	"one_fm", "one_fm", "page", "transportation_manifest_page",
	"transportation_manifest_page.js"
))


class TestBothScreensOrderVehiclesTheSameWay(FrappeTestCase):
	"""AC1."""

	def test_the_schedule_orders_by_vehicle_name(self):
		source = inspect.getsource(transportation_schedule.build_vehicle_list)
		self.assertIn('order_by="name asc"', source)

	def test_the_manifest_sorts_its_vehicles_too(self):
		source = inspect.getsource(transportation_schedule.get_manifest_data_for_plan)
		self.assertIn("vehicle_order.sort()", source)

	def test_the_sort_happens_after_the_rows_are_grouped(self):
		# Sorting the keys but iterating the rows would leave the routes and the vehicle
		# list in different orders, which is a worse bug than the one being fixed.
		source = inspect.getsource(transportation_schedule.get_manifest_data_for_plan)
		self.assertLess(source.index("vehicle_items[row.vehicle].append(row)"),
						source.index("vehicle_order.sort()"))
		self.assertLess(source.index("vehicle_order.sort()"),
						source.index("for vi, vid in enumerate(vehicle_order):"))

	def test_each_vehicles_own_trips_keep_their_order(self):
		# Only the vehicles are re-ordered; a bus's runs stay in the order they were
		# saved, which is the order it drives them.
		source = inspect.getsource(transportation_schedule.get_manifest_data_for_plan)
		self.assertNotIn("vehicle_items[row.vehicle].sort", source)


class TestTheTabBarCanBeNavigated(FrappeTestCase):
	"""AC2, AC3, AC4."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.sheet = SHEET.read_text()

	def test_there_is_a_search_box(self):
		self.assertIn('id="mfst-vehicle-search"', self.sheet)

	def test_it_matches_id_plate_model_and_driver(self):
		# The three things a supervisor is holding when they come looking.
		self.assertIn("[pr.label, meta.license_plate, meta.model, meta.driver]", self.sheet)

	def test_the_haystack_is_stamped_on_the_tab(self):
		# Filtering from the tab itself cannot disagree with what is rendered; going
		# back to ROUTE_DATA could.
		self.assertIn("tab.dataset.search = haystack;", self.sheet)

	def test_a_filtered_tab_is_hidden_not_disabled(self):
		# AC2 says the dispatcher must be able to SELECT a match while the filter is
		# active, so matches stay fully clickable.
		self.assertIn("tab.hidden = q ?", self.sheet)
		self.assertNotIn("tab.disabled = q", self.sheet)

	def test_the_skipped_tab_is_not_matched_by_a_vehicle_search(self):
		# It carries no vehicle, so it cannot answer a vehicle query.
		self.assertIn('tab.classList.contains("mfst-skipped-tab") ? null : ""', self.sheet)

	def test_both_arrows_scroll_the_strip(self):
		self.assertIn('prevBtn.addEventListener("click", () => scrollTabs(-1));', self.sheet)
		self.assertIn('nextBtn.addEventListener("click", () => scrollTabs(1));', self.sheet)
		self.assertIn('behavior: "smooth"', self.sheet)

	def test_a_click_moves_by_a_page_not_to_an_edge(self):
		# Jumping to the end loses the dispatcher's place.
		self.assertIn("Math.max(160, tabBar.clientWidth * 0.8)", self.sheet)

	def test_the_arrows_disable_at_the_ends(self):
		self.assertIn("prevBtn.disabled = atStart;", self.sheet)
		self.assertIn("nextBtn.disabled = atEnd;", self.sheet)

	def test_the_overflow_count_is_measured_not_assumed(self):
		# A filter changes which tabs exist; a fixed count would keep announcing the
		# ones it just hid.
		self.assertIn("const visible = [...tabBar.querySelectorAll(\".mfst-tab\")].filter(t => !t.hidden);",
					  self.sheet)
		self.assertIn("if (r.right <= bar.left + 1) left++;", self.sheet)

	def test_the_badge_reads_the_way_the_criterion_writes_it(self):
		self.assertIn('parts.push(`\\u25c4 ${left} more`);', self.sheet)
		self.assertIn('parts.push(`${right} more \\u25ba`);', self.sheet)

	def test_the_fades_never_swallow_a_click(self):
		self.assertIn("pointer-events: none; z-index: 1; opacity: 0;", self.sheet)

	def test_the_indicators_resync_on_scroll_and_resize(self):
		self.assertIn('tabBar.addEventListener("scroll", syncTabOverflow, { passive: true });',
					  self.sheet)
		self.assertIn('window.addEventListener("resize", syncTabOverflow);', self.sheet)


class TestPruningDoesNotStrandTheManifest(FrappeTestCase):
	"""The latent bug: force=True deletes past the links pointing at it."""

	def test_the_prune_releases_manifest_references_first(self):
		source = inspect.getsource(shipment_generator._prune_stale)
		self.assertIn("_release_manifest_references(row.name)", source)
		self.assertLess(source.index("_release_manifest_references(row.name)"),
						source.index("frappe.delete_doc("))

	def test_only_the_provenance_link_is_cleared(self):
		# The row's employee, stop and attendance are facts about the journey, not about
		# the card the demand was generated on.
		source = inspect.getsource(shipment_generator._release_manifest_references)
		self.assertIn('"transportation_shipment", None,', source)
		self.assertIn("update_modified=False", source)
		for kept in ("employee", "attendance_status", "stop_sequence"):
			self.assertNotIn(f'"{kept}"', source)

	def test_a_released_row_survives_its_shipment(self):
		shipment = frappe.new_doc("Transportation Shipment")
		shipment.status = "Unassigned"
		shipment.trip_direction = "Outward"
		shipment.flags.ignore_mandatory = True
		shipment.flags.ignore_links = True
		shipment.insert(ignore_permissions=True)

		manifest = frappe.new_doc("Transportation Manifest")
		manifest.schedule_date = frappe.utils.today()
		manifest.append("transportation_manifest_details", {
			"employee_action": "Boarding",
			"stop_sequence": 1,
			"transportation_shipment": shipment.name,
		})
		manifest.flags.ignore_mandatory = True
		manifest.flags.ignore_links = True
		manifest.insert(ignore_permissions=True)

		shipment_generator._release_manifest_references(shipment.name)
		frappe.delete_doc("Transportation Shipment", shipment.name,
						  ignore_permissions=True, force=True)

		manifest.reload()
		row = manifest.transportation_manifest_details[0]
		self.assertIsNone(row.transportation_shipment)
		self.assertEqual(row.employee_action, "Boarding")
		# The manifest can still be saved, which is what the dangling link prevented.
		manifest.flags.ignore_mandatory = True
		manifest.flags.ignore_links = True
		manifest.save(ignore_permissions=True)
