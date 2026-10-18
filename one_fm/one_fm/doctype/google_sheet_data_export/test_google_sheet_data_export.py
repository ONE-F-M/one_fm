# Copyright (c) 2023, ONE FM and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, now_datetime

from one_fm.one_fm.doctype.google_sheet_data_export import exporter

DOCTYPE = "Google Sheet Data Export"


class TestGoogleSheetDataExport(FrappeTestCase):
	def setUp(self):
		frappe.db.set_value(DOCTYPE, {"enable_auto_update": 1}, "enable_auto_update", 0)

	def _export(self, frequency, last_run):
		doc = frappe.get_doc(
			{
				"doctype": DOCTYPE,
				"reference_doctype": "ToDo",
				"enable_auto_update": 1,
				"update_frequency": frequency,
				"last_execution_timestamp": last_run,
			}
		).insert()
		return doc.name

	def _enqueued(self, run):
		with patch.object(exporter, "enqueue_export") as m_enqueue:
			run()
		return [call.args[0] for call in m_enqueue.call_args_list]

	def test_hourly_run_picks_every_hourly_export_and_no_daily_one(self):
		hourly_a = self._export("Hourly", now_datetime())
		hourly_b = self._export("Hourly", add_days(now_datetime(), -3))
		self._export("Daily", add_days(now_datetime(), -1))

		self.assertCountEqual(self._enqueued(exporter.update_google_sheet_hourly), [hourly_a, hourly_b])

	def test_daily_run_picks_a_daily_export_last_run_yesterday(self):
		self._export("Hourly", add_days(now_datetime(), -1))
		daily = self._export("Daily", add_days(now_datetime(), -1))

		self.assertEqual(self._enqueued(exporter.update_google_sheet_daily), [daily])

	def test_daily_run_skips_a_daily_export_already_run_today(self):
		self._export("Daily", now_datetime())

		self.assertEqual(self._enqueued(exporter.update_google_sheet_daily), [])

	def test_last_execution_is_a_timestamp(self):
		field = frappe.get_meta(DOCTYPE).get_field("last_execution_timestamp")

		self.assertEqual(field.fieldtype, "Datetime")
		self.assertIsNone(frappe.get_meta(DOCTYPE).get_field("last_execution_date"))
