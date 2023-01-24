# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE
from __future__ import print_function

import os.path

import csv
import os
import re
import json

import frappe
import frappe.permissions
from frappe import _
from frappe.core.doctype.access_log.access_log import make_access_log
from frappe.utils import cint, cstr, format_datetime, format_duration, formatdate, parse_json
from frappe.utils.csvutils import UnicodeWriter

import google.auth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient import discovery

from google.oauth2 import service_account


def get_data_keys():
	return frappe._dict(
		{
			"data_separator": _("Start entering data below this line"),
			"main_table": _("Table") + ":",
			"parent_table": _("Parent Table") + ":",
			"columns": _("Column Name") + ":",
			"doctype": _("DocType") + ":",
		}
	)
	
@frappe.whitelist()
def export_data(
	doctype=None,
	parent_doctype=None,
	all_doctypes=True,
	with_data=False,
	select_columns=None,
	template=False,
	filters=None,
	link=None,
	google_sheet_id=None,
	sheet_name=None,
	owner=None
):
	_doctype = doctype
	if isinstance(_doctype, list):
		_doctype = _doctype[0]
	make_access_log(
		doctype=_doctype,
		columns=select_columns,
		filters=filters,
		method=parent_doctype,
	)
	exporter = DataExporter(
		doctype=doctype,
		parent_doctype=parent_doctype,
		all_doctypes=all_doctypes,
		with_data=with_data,
		select_columns=select_columns,
		template=template,
		filters=filters,
		link=link,
		google_sheet_id=google_sheet_id,
		sheet_name=sheet_name,
		owner=owner
	)
	result = exporter.build_response()

	return result


class DataExporter:
	def __init__(
		self,
		doctype=None,
		parent_doctype=None,
		all_doctypes=True,
		with_data=False,
		select_columns=None,
		template=False,
		filters=None,
		link=None,
		google_sheet_id=None,
		sheet_name=None,
		owner=None
	):
		self.doctype = doctype
		self.parent_doctype = parent_doctype
		self.all_doctypes = all_doctypes
		self.with_data = cint(with_data)
		self.select_columns = select_columns
		self.template = template
		self.filters = filters
		self.data_keys = get_data_keys()
		self.google_sheet_id = google_sheet_id
		self.link = link
		self.sheet_name = sheet_name
		self.owner = owner

		self.prepare_args()

	def init_google_sheet_service(self):
		SERVICE_ACCOUNT_FILE = cstr(frappe.local.site) + frappe.local.conf.google_sheet

		SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

		credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

		service = discovery.build('sheets', 'v4', credentials=credentials)
		drive_api = build('drive', 'v3', credentials=credentials)

		service_collection = {'service':service, 'drive_api':drive_api}

		return service_collection

	def prepare_args(self):
		if self.select_columns:
			self.select_columns = parse_json(self.select_columns)
		if self.filters:
			self.filters = parse_json(self.filters)
		self.docs_to_export = {}
		if self.doctype:
			if isinstance(self.doctype, str):
				self.doctype = [self.doctype]

			if len(self.doctype) > 1:
				self.docs_to_export = self.doctype[1]
			self.doctype = self.doctype[0]

		if not self.parent_doctype:
			self.parent_doctype = self.doctype

		self.column_start_end = {}

		if self.all_doctypes:
			self.child_doctypes = []
			for df in frappe.get_meta(self.doctype).get_table_fields():
				self.child_doctypes.append(dict(doctype=df.options, parentfield=df.fieldname))
		
		if not self.sheet_name:
			self.sheet_name = 'sheet1'

	def build_response(self):
		self.writer = UnicodeWriter()
		self.name_field = "parent" if self.parent_doctype != self.doctype else "name"
		service = self.init_google_sheet_service()
		print(service)
		self.writer.writerow([""])
		self.labelrow = []
		self.fieldrow = []

		self.columns = []

		self.build_field_columns(self.doctype)
		
		self.column = self.labelrow
		values = self.add_data()

		if not self.link:
			self.create(service)

		if not self.check_if_sheet_exist(service):
			self.add_sheet(service)
		self.update_sheet(values, service)
		# print(self.data)
		if self.with_data and not values:
			frappe.respond_as_web_page(
				_("No Data"), _("There is no data to be exported"), indicator_color="orange"
			)
		result = {"google_sheet_id":self.google_sheet_id, "link":self.link,"sheet_name":self.sheet_name}
		return result


	def build_field_columns(self, dt, parentfield=None):
		meta = frappe.get_meta(dt)

		# build list of valid docfields
		tablecolumns = []
		table_name = "tab" + dt
		for f in frappe.db.get_table_columns_description(table_name):
			field = meta.get_field(f.name)
			if field and (
				(self.select_columns and f.name in self.select_columns[dt]) or not self.select_columns
			):
				tablecolumns.append(field)

		tablecolumns.sort(key=lambda a: int(a.idx))

		_column_start_end = frappe._dict(start=0)

		if dt == self.doctype:
			if (meta.get("autoname") and meta.get("autoname").lower() == "prompt") or (self.with_data):
				self._append_name_column()

			# if importing only child table for new record, add parent field
			if meta.get("istable") and not self.with_data:
				self.append_field_column(
					frappe._dict(
						{
							"fieldname": "parent",
							"parent": "",
							"label": "Parent",
							"fieldtype": "Data",
							"reqd": 1,
							"info": _("Parent is the name of the document to which the data will get added to."),
						}
					),
					True,
				)

			_column_start_end = frappe._dict(start=0)
		else:
			_column_start_end = frappe._dict(start=len(self.columns))

			if self.with_data:
				self._append_name_column(dt)

		for docfield in tablecolumns:
			self.append_field_column(docfield, True)

		# all non mandatory fields
		for docfield in tablecolumns:
			self.append_field_column(docfield, False)


		_column_start_end.end = len(self.columns) + 1

		self.column_start_end[(dt, parentfield)] = _column_start_end

	def append_field_column(self, docfield, for_mandatory):
		if not docfield:
			return
		if for_mandatory and not docfield.reqd:
			return
		if not for_mandatory and docfield.reqd:
			return
		if docfield.fieldname in ("parenttype", "trash_reason"):
			return
		if docfield.hidden:
			return
		if (
			self.select_columns
			and docfield.fieldname not in self.select_columns.get(docfield.parent, [])
			and docfield.fieldname != "name"
		):
			return

		self.fieldrow.append(docfield.fieldname)
		self.labelrow.append(_(docfield.label))

	def add_field_headings(self):
		self.writer.writerow(self.labelrow)

	def add_data(self):
		from frappe.query_builder import DocType

		if self.template and not self.with_data:
			return

		frappe.permissions.can_export(self.parent_doctype, raise_exception=True)

		# sort nested set doctypes by `lft asc`
		order_by = None
		table_columns = frappe.db.get_table_columns(self.parent_doctype)
		if "lft" in table_columns and "rgt" in table_columns:
			order_by = f"`tab{self.parent_doctype}`.`lft` asc"
		# get permitted data only
		self.data = frappe.get_list(
			self.doctype, fields=self.fieldrow, filters=self.filters, limit_page_length=None, order_by=order_by
		)
			# add main table
		rows = [self.fieldrow]
		for doc in self.data:
			row = []
			for field in self.fieldrow:
				row.append(doc[field])
			rows.append(row)

		return rows

	def add_data_row(self, rows, dt, parentfield, doc, rowidx):
		d = doc.copy()
		meta = frappe.get_meta(dt)
		if self.all_doctypes:
			d.name = f'"{d.name}"'

		if len(rows) < rowidx + 1:
			rows.append([""] * (len(self.columns) + 1))
		row = rows[rowidx]

		_column_start_end = self.column_start_end.get((dt, parentfield))


		if _column_start_end:
			for i, c in enumerate(self.columns[_column_start_end.start : _column_start_end.end]):
				df = meta.get_field(c)
				fieldtype = df.fieldtype if df else "Data"
				value = d.get(c, "")
				if value:
					if fieldtype == "Date":
						value = formatdate(value)
					elif fieldtype == "Datetime":
						value = format_datetime(value)
					elif fieldtype == "Duration":
						value = format_duration(value, df.hide_days)

				row[_column_start_end.start + i + 1] = value
		
	def _append_name_column(self, dt=None):
		self.append_field_column(
			frappe._dict(
				{
					"fieldname": "name" if dt else self.name_field,
					"parent": dt or "",
					"label": "ID",
					"fieldtype": "Data",
					"reqd": 1,
				}
			),
			True,
		)

	def create(self, services):
		"""
		BEFORE RUNNING:
		---------------
		1. If not already done, enable the Google Sheets API
		and check the quota for your project at
		https://console.developers.google.com/apis/api/sheets
		2. Install the Python client library for Google APIs by running
		`pip install --upgrade google-api-python-client`
		"""
		from pprint import pprint


		# TODO: Change placeholder below to generate authentication credentials. See
		# https://developers.google.com/sheets/quickstart/python#step_3_set_up_the_sample
		#
		# Authorize using one of the following scopes:
		#     'https://www.googleapis.com/auth/drive'
		#     'https://www.googleapis.com/auth/drive.file'
		#     'https://www.googleapis.com/auth/spreadsheets'

		service = services["service"]
		drive_api = services["drive_api"]

		domain_permission = {
			'type': 'user',
			'role': 'writer',
			'emailAddress': "{0}".format(self.owner)
		}
		spreadsheet = {
				'properties': {
				'title': "{0}".format(self.doctype)
				},
				"sheets": [
					{
						"properties": {
							"sheetId": 1,
							"title": "{0}".format(self.sheet_name)
						},
					}
				]
			}
		request = service.spreadsheets().create(body=spreadsheet).execute()

		#Grant Permission 
		permission = drive_api.permissions().create(
					fileId=request["spreadsheetId"],
					body=domain_permission,
				).execute()
		print(request)
		self.google_sheet_id = request["spreadsheetId"]
		self.link = request["spreadsheetUrl"]

	def check_if_sheet_exist(self, services):
		service = services["service"]

		sheet_metadata = service.spreadsheets().get(spreadsheetId=self.google_sheet_id).execute()
		
		sheets = sheet_metadata.get('sheets', '')
		sheetNames = []
		for i in range(len(sheets)):
			sheetNames.append(sheets[i].get("properties").get("title"))

		if self.sheet_name in sheetNames:
			return True
		return False

	def add_sheet(self, services):
		try:
			service = services["service"]

			request_body = {
				'requests': [{
					'addSheet': {
						'properties': {
							'title': self.sheet_name,
						}
					}
				}]
			}

			response = service.spreadsheets().batchUpdate(
				spreadsheetId=self.google_sheet_id,
				body=request_body
			).execute()

			return response
		except Exception as e:
			print(e)


	def update_sheet(self, values, services):
		"""Shows basic usage of the Sheets API.
		Prints values from a sample spreadsheet.
		"""
		try:
			service = services["service"]

			no_of_row = len(values)
			no_of_col = len(self.column)
			ranges = self.sheet_name + "!A1:" + chr(ord('A') + no_of_col) + str(no_of_row)

			# clear sheet
			service.spreadsheets().values().clear(spreadsheetId=self.google_sheet_id, 
				range='{0}!A1:Z'.format(self.sheet_name), body={}).execute()

			# add new value
			result = service.spreadsheets().values().update(
						spreadsheetId=self.google_sheet_id, range=ranges,valueInputOption="USER_ENTERED", body={"values":values}).execute()

			
			# request = service.spreadsheets().values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID, range="Country!A1:B22").execute()
			# request = service.spreadsheets().values().update(spreadsheetId=SAMPLE_SPREADSHEET_ID, range="Country!A24", valueInputOption="USER_ENTERED", body={"values":aoa}).execute()
			

			
			return result
		except HttpError as err:
			print(err)

@frappe.whitelist()
def update_google_sheet_daily():
	list_of_export = frappe.get_list("Google Sheet Data Export",{"enable_auto_update":1}, ['name'])

	for e in list_of_export:
		doc = frappe.get_doc("Google Sheet Data Export",e.name)

		select_columns = doc.field_cache
		filters = doc.filter_cache

		frappe.enqueue(export_data, 
			doctype= doc.reference_doctype,
			select_columns= select_columns,
			filters= filters,
			link= doc.link,
			google_sheet_id= doc.google_sheet_id,
			sheet_name= doc.sheet_name,
			owner= doc.owner, 
			is_async=True, queue="long")