# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""A generation run that reads no demand must not delete the whole pool.

Found while testing Operations-023, on live-ish data: one click on Generate Shipments
deleted 551 unassigned cards, and a second click could not bring them back.

The chain is short and every link is ordinary:

    get_grouped_employees_by_accommodation()  ->  {}
    current_keys                              ->  set()
    _prune_stale(set())                       ->  "not in current_keys" is true for ALL

The demand builder returns an empty dict for several unremarkable reasons - no Active
Operations Shift, nobody allocated to one, or no Accommodation Checkin Checkout carrying
an employee. The last of those is what happened: the site had 120 IN rows and every one
of them belonged to an external contract tenant with no employee link. The builder logs
that as a degraded state rather than raising, so what reached the caller was an empty
dict indistinguishable from "nobody needs a bus today".

The guard is one line at the call site, and these tests are mostly about where it must
NOT go: remove_unassigned_shipments_for_trip_request deliberately passes an empty key set
to clear one trip request's cards, so the same guard inside the prune would break a
working feature.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.transportation_shipment import shipment_generator

SEEDED = "WI-002591-GUARD-"


def _clear():
	frappe.db.delete("Transportation Shipment", {"name": ["like", SEEDED + "%"]})


def _card(suffix, generation_key, status="Unassigned", source="Operations Shift"):
	doc = frappe.new_doc("Transportation Shipment")
	doc.name = SEEDED + suffix
	doc.status = status
	doc.source_doctype = source
	doc.generation_key = generation_key
	doc.db_insert()
	return doc.name


class TestAnEmptyRunPrunesNothing(FrappeTestCase):
	"""The whole point: no demand read means no authority to delete."""

	def setUp(self):
		_clear()
		self.addCleanup(_clear)
		self.pruned_with = []
		real = shipment_generator._prune_stale
		shipment_generator._prune_stale = self._spy(real)
		self.addCleanup(setattr, shipment_generator, "_prune_stale", real)

	def _spy(self, real):
		def wrapped(current_keys):
			self.pruned_with.append(set(current_keys))
			return real(current_keys)
		return wrapped

	def _run(self, demands):
		real_map = shipment_generator.get_grouped_employees_by_accommodation
		real_build = shipment_generator.build_demand_descriptors
		shipment_generator.get_grouped_employees_by_accommodation = lambda: {"x": 1} if demands else {}
		shipment_generator.build_demand_descriptors = lambda nested: demands
		self.addCleanup(setattr, shipment_generator, "get_grouped_employees_by_accommodation", real_map)
		self.addCleanup(setattr, shipment_generator, "build_demand_descriptors", real_build)
		return shipment_generator.generate_transportation_shipments()

	def test_a_card_survives_a_run_that_read_no_demand(self):
		# This is the 551 cards, in miniature.
		name = _card("SURVIVES", "OPS|GONE|Night|Site")

		self._run(demands=[])

		self.assertTrue(frappe.db.exists("Transportation Shipment", name))

	def test_the_prune_is_not_called_at_all(self):
		_card("NOTCALLED", "OPS|GONE|Night|Site")

		self._run(demands=[])

		self.assertEqual(self.pruned_with, [])

	def test_the_summary_says_it_did_not_prune(self):
		# The canvas reads this to warn instead of reporting a quiet success.
		summary = self._run(demands=[])

		self.assertFalse(summary["pruned"])
		self.assertEqual(summary["deleted"], 0)

	def test_a_demand_with_no_riders_is_still_no_demand(self):
		# build_demand_descriptors can return rows whose employees list is empty; the loop
		# skips those, so current_keys stays empty and the guard must still hold.
		name = _card("NORIDERS", "OPS|GONE|Night|Site")

		summary = self._run(demands=[{"employees": [], "camp": "ACC-01"}])

		self.assertFalse(summary["pruned"])
		self.assertTrue(frappe.db.exists("Transportation Shipment", name))


class TestAGoodRunStillPrunes(FrappeTestCase):
	"""The guard must not turn the prune off in general - stale cards still have to go.

	Exercised against the real _prune_stale rather than restating the condition, because
	the failure this protects against is "the fix quietly stopped pruning anything".
	"""

	def setUp(self):
		_clear()
		self.addCleanup(_clear)

	def _keys_sparing_everything_but(self, *stale_keys):
		"""Every key currently in the pool, minus the ones this test wants pruned.

		_prune_stale sweeps the WHOLE pool, so handing it a bare {"one key"} would mark
		every real card on the site stale and delete it. The rollback would put them back,
		but a test that destroys the pool to prove the pool is not destroyed is one commit
		away from being the bug it is testing for.
		"""
		keys = frappe.get_all(
			"Transportation Shipment",
			filters={"source_doctype": "Operations Shift", "status": "Unassigned"},
			pluck="generation_key",
		)
		return {k for k in keys if k and k not in stale_keys}

	def test_a_card_whose_demand_is_gone_is_still_deleted(self):
		stale = _card("STALE", "OPS|GONE|Night|Site")

		deleted = shipment_generator._prune_stale(
			self._keys_sparing_everything_but("OPS|GONE|Night|Site")
		)

		self.assertEqual(deleted, 1)
		self.assertFalse(frappe.db.exists("Transportation Shipment", stale))

	def test_a_card_whose_demand_still_exists_is_kept(self):
		live = _card("LIVE", "OPS|ACC-01|Day|Site")

		deleted = shipment_generator._prune_stale(self._keys_sparing_everything_but())

		self.assertEqual(deleted, 0)
		self.assertTrue(frappe.db.exists("Transportation Shipment", live))

	def test_a_placed_card_is_never_pruned(self):
		# Only Unassigned cards are the pool's to reclaim; an Assigned one belongs to a lane.
		placed = _card("PLACED", "OPS|GONE|Night|Site", status="Assigned")

		shipment_generator._prune_stale(
			self._keys_sparing_everything_but("OPS|GONE|Night|Site")
		)

		self.assertTrue(frappe.db.exists("Transportation Shipment", placed))

	def test_a_trip_request_card_is_never_pruned_by_the_shift_run(self):
		other = _card("TRIPREQ", "TR|GONE|Day|Site", source="Trip Request")

		shipment_generator._prune_stale(
			self._keys_sparing_everything_but("TR|GONE|Day|Site")
		)

		self.assertTrue(frappe.db.exists("Transportation Shipment", other))


class TestWhereTheGuardMustNotGo(FrappeTestCase):
	def setUp(self):
		_clear()
		self.addCleanup(_clear)

	def test_clearing_one_trip_requests_cards_still_works(self):
		# remove_unassigned_shipments_for_trip_request calls the trip-request prune with an
		# EMPTY key set on purpose. The same guard inside the prune would silently turn that
		# feature off, so it lives at the shift generator's call site instead.
		import inspect

		source = inspect.getsource(shipment_generator.remove_unassigned_shipments_for_trip_request)
		self.assertIn("current_keys=set()", source)

	def test_the_trip_request_prune_has_no_empty_key_guard(self):
		import inspect

		source = inspect.getsource(shipment_generator._prune_stale_for_trip_request)
		self.assertNotIn("if not current_keys", source)

	def test_the_shift_prune_itself_is_unchanged(self):
		# The guard is at the call site, so _prune_stale keeps its single job: delete the
		# unassigned shift cards whose demand is gone.
		import inspect

		source = inspect.getsource(shipment_generator._prune_stale)
		self.assertIn('"source_doctype": "Operations Shift"', source)
		self.assertIn('"status": "Unassigned"', source)


class TestTheCanvasSaysSomething(FrappeTestCase):
	def test_the_button_warns_instead_of_reporting_a_quiet_success(self):
		# "0 created, 0 updated, 0 removed" in green is what the dispatcher saw after the
		# pool had already gone.
		js = frappe.read_file(
			frappe.get_app_path(
				"one_fm", "one_fm", "page", "transportation_schedule", "transportation_schedule.js"
			)
		)
		self.assertIn("s.pruned === false", js)
		self.assertIn("orange", js.split("s.pruned === false", 1)[1][:600])
