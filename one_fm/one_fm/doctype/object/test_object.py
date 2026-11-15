# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from one_fm.one_fm.doctype.object.test_object_processa_scripts import NO_COMMIT, install_scripts, run


def setUpModule():
	NO_COMMIT.start()


def tearDownModule():
	NO_COMMIT.stop()


def make_template(parts):
	template = frappe.get_doc({"doctype": "Object Template", "template_name": "TEST-OBJ-TEMPLATE"})
	for part in parts:
		template.append("object_template_items", {"item_name": part, "description": f"{part} description"})
	template.insert(ignore_permissions=True, ignore_mandatory=True)
	return template.name


def make_object(**fields):
	obj = frappe.get_doc({"doctype": "Object", "object_name": "TEST-OBJ", **fields})
	obj.insert(ignore_mandatory=True, ignore_permissions=True)
	return obj


class TestObject(FrappeTestCase):
	def setUp(self):
		install_scripts()

	def test_a_future_commissioning_date_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			make_object(commissioning_date=add_days(today(), 1))

	def test_last_service_date_defaults_to_commissioning_date(self):
		obj = make_object(commissioning_date=add_days(today(), -10))
		self.assertEqual(str(obj.last_service_date), add_days(today(), -10))

	def test_a_set_last_service_date_is_kept(self):
		obj = make_object(commissioning_date=add_days(today(), -10), last_service_date=add_days(today(), -2))
		self.assertEqual(str(obj.last_service_date), add_days(today(), -2))

	def test_template_parts_fill_an_empty_table_only(self):
		template = make_template(["Belt", "Filter"])
		obj = make_object(object_template=template)
		self.assertEqual([d.item_name for d in obj.object_items], ["Belt", "Filter"])

		obj.object_items = obj.object_items[:1]
		obj.save(ignore_permissions=True)
		self.assertEqual([d.item_name for d in obj.object_items], ["Belt"])

	def test_the_map_step_saves_the_prepared_object(self):
		obj = make_object(commissioning_date=add_days(today(), -5))
		frappe.db.set_value("Object", obj.name, "last_service_date", None)
		obj.reload()

		result = run("Prepare Object", obj)

		self.assertEqual(result["object_prepared"], obj.name)
		self.assertEqual(str(frappe.db.get_value("Object", obj.name, "last_service_date")), add_days(today(), -5))
