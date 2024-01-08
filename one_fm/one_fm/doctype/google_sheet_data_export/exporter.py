# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE
from __future__ import print_function

import os.path

import csv
import os
import re
import json
import time

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
import gspread
from frappe.utils import get_site_name

from google.oauth2 import service_account
import os

@frappe.whitelist()
def export_data(
	doctype=None,
	parent_doctype=None,
	all_doctypes=True,
	with_data=False,
	select_columns=None,
	filters=None,
	link=None,
	google_sheet_id=None,
	sheet_name=None,
	owner=None,
	client_id = None
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
		filters=filters,
		link=link,
		google_sheet_id=google_sheet_id,
		sheet_name=sheet_name,
		owner=owner,
		client_id = client_id
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
		filters=None,
		link=None,
		google_sheet_id=None,
		sheet_name=None,
		owner=None,
		client_id = None
	):
		self.doctype = doctype
		self.parent_doctype = parent_doctype
		self.all_doctypes = all_doctypes
		self.with_data = cint(with_data)
		self.select_columns = select_columns
		self.filters = filters
		self.google_sheet_id = google_sheet_id
		self.link = link
		self.sheet_name = sheet_name
		self.owner = owner
		self.cell_colour = []
		self.client_id = client_id

		api = self.initialize_service()
		self.service = api["service"]
		self.drive_api = api["drive_api"]
		self.credentials = api["credentials"]
		
		self.prepare_args()
	
	def initialize_service(self):
		#initialize Google Sheet Service

		SERVICE_ACCOUNT_FILE = os.getcwd()+"/"+cstr(frappe.local.site) + frappe.local.conf.google_sheet

		SCOPES = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

		credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

		service = discovery.build('sheets', 'v4', credentials=credentials)
		drive_api = build('drive', 'v3', credentials=credentials)
		
		return {"credentials":credentials, "service": service, "drive_api": drive_api}

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

		self.writer.writerow([""])
		self.labelrow = []
		self.fieldrow = []

		self.columns = []

		self.build_field_columns(self.doctype)
		
		if self.all_doctypes:
			for d in self.child_doctypes:
				if (
					self.select_columns and self.select_columns.get(d["doctype"], None)
				) or not self.select_columns:
					self.build_field_columns(d["doctype"], d["parentfield"])
	
		self.column = self.labelrow
		values = self.add_data()

		if self.with_data and not values:
			frappe.msgprint(
				_("No Data"), _("There is no data to be exported"), indicator_color="orange"
			)
		
		if not self.link:
			self.create()
		sheet = self.build_connection_with_sheet()
		if not sheet:
			frappe.msgprint(frappe._("We do not have access to this sheet. Kindly, share your sheet with the following:<br><br> <b>{0}</b>").format(str(self.client_id)), 
					indicator="red", 
					title = "Warning")
		else:
			if not self.check_if_sheet_exist(sheet):
				self.add_sheet()

			self.update_sheet(values)
			self.batch_update(sheet)

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

		fields = [ sub['name'] for sub in frappe.db.get_table_columns_description(table_name) ]
		for f in self.select_columns[dt]:
			field = meta.get_field(f)
			if field:
				tablecolumns.append(field)

		# tablecolumns.sort(key=lambda a: int(a.idx))

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
					)
				)

			_column_start_end = frappe._dict(start=0)
		else:
			_column_start_end = frappe._dict(start=len(self.columns))

			if self.with_data:
				self._append_name_column(dt)


		for docfield in tablecolumns:
			self.append_field_column(docfield)

		_column_start_end.end = len(self.columns) + 1

		self.column_start_end[(dt, parentfield)] = _column_start_end

	def append_field_column(self, docfield):
		if not docfield:
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
		if docfield.parent and docfield.parent != self.doctype:
			self.labelrow.append(f"{_(docfield.label)}({_(docfield.parent)})")
		else:
			self.labelrow.append(_(docfield.label))

		self.fieldrow.append(docfield.fieldname)
		self.columns.append(docfield.fieldname)

	def add_field_headings(self):
		self.writer.writerow(self.labelrow)

	def add_data(self):
		from frappe.query_builder import DocType

		data = []
		data.append(self.labelrow)
		# sort nested set doctypes by `lft asc`
		order_by = None
		table_columns = frappe.db.get_table_columns(self.parent_doctype)
		if "lft" in table_columns and "rgt" in table_columns:
			order_by = f"`tab{self.parent_doctype}`.`lft` asc"
		# get permitted data only
		self.data = frappe.get_list(
			self.doctype, fields=["*"], filters=self.filters, limit_page_length=None, order_by=order_by
		)
		cell_colour = []
		row_index = 0
		for doc in self.data:
			# add main table
			rows = []
			self.add_data_row(rows, self.doctype, None, doc, 0, cell_colour, row_index)

			if self.all_doctypes:
				# add child tables
				for c in self.child_doctypes:
					child_doctype_table = DocType(c["doctype"])
					data_row = (
						frappe.qb.from_(child_doctype_table)
						.select("*")
						.where(child_doctype_table.parent == doc.name)
						.where(child_doctype_table.parentfield == c["parentfield"])
						.orderby(child_doctype_table.idx)
					)
					for ci, child in enumerate(data_row.run(as_dict=True)):
						self.add_data_row(rows, c["doctype"], c["parentfield"], child, ci, cell_colour, row_index)
			
			for row in rows:
				data.append(row)
			row_index += 1
		self.cell_colour = cell_colour
		return data

	def add_data_row(self, rows, dt, parentfield, doc, rowidx, cell_colour, row_index):
		d = doc.copy()
		meta = frappe.get_meta(dt)
		if self.all_doctypes:
			d.name = f'"{d.name}"'


		_column_start_end = self.column_start_end.get((dt, parentfield))
		if _column_start_end:
			if len(rows) < rowidx + 1:
				rows.append([""] * (len(self.columns) + 1))
			row = rows[rowidx]
			for i, c in enumerate(self.columns[_column_start_end.start : _column_start_end.end]):
				df = meta.get_field(c)
				value = str(d.get(c, ""))
				value = remove_quotes(value)
				# check if value size is greater than 50000
				if len(value) >= 50000:
					cell_colour.append({'column':_column_start_end.start + i, 'row':row_index+1})
					row[_column_start_end.start + i] = f"ERROR - Description Length is more than 50,000 so can not import Data"
				else:
					row[_column_start_end.start + i] = value

		
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
			)
		)

	def build_connection_with_sheet(self):
		api = self.initialize_service()
		service = api["service"]
		try:
			if self.google_sheet_id:
				sheet = service.spreadsheets().get(spreadsheetId=self.google_sheet_id,ranges=[], includeGridData=False).execute()
				return sheet
			if not self.google_sheet_id:
				return True
		except HttpError as err:
			return False

	def create(self):
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

		service = self.service
		drive_api = self.drive_api

		# TODO: Change placeholder below to generate authentication credentials. See
		# https://developers.google.com/sheets/quickstart/python#step_3_set_up_the_sample
		#
		# Authorize using one of the following scopes:
		#     'https://www.googleapis.com/auth/drive'
		#     'https://www.googleapis.com/auth/drive.file'
		#     'https://www.googleapis.com/auth/spreadsheets'

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
		self.google_sheet_id = request["spreadsheetId"]
		self.link = request["spreadsheetUrl"]

	def check_if_sheet_exist(self, sheet_metadata):
		service = self.service
		try:
			# sheet_metadata = service.spreadsheets().get(spreadsheetId=self.google_sheet_id).execute()
			
			sheets = sheet_metadata.get('sheets', '')
			sheetNames = []
			for i in range(len(sheets)):
				sheetNames.append(sheets[i].get("properties").get("title"))

			if self.sheet_name in sheetNames:
				return True
			return False
		except HttpError as err:
			frappe.throw(_("This sheet is not linked"))

	def add_sheet(self):
		service = self.service
		try:
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
			frappe.log_error(e)


	def update_sheet(self, values):
		"""Shows basic usage of the Sheets API.
		Prints values from a sample spreadsheet.
		"""
		service = self.service
		try:
			no_of_row = len(values)
			no_of_col = len(self.column)
			if no_of_col <= 26:
				ranges = self.sheet_name + "!A1:" + chr(ord('A') + no_of_col) + str(no_of_row)
			else:
				ranges = self.sheet_name + "!A1:A" + chr(ord('A') + no_of_col - 26) + str(no_of_row)

			# clear sheet
			service.spreadsheets().values().clear(spreadsheetId=self.google_sheet_id, 
				range='{0}'.format(self.sheet_name), body={}).execute()

			# add new value
			result = service.spreadsheets().values().update(
						spreadsheetId=self.google_sheet_id, range=ranges,valueInputOption="USER_ENTERED", body={"values":values}).execute()

			
			# request = service.spreadsheets().values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID, range="Country!A1:B22").execute()
			

			
			return result
		except HttpError as err:
			frappe.log_error(err)

	def batch_update(self, sheet):
		'''
			This method is to update the cell that have errors in displaying the value.
		'''
		# get spreadsheet details
		service = self.service
		client = gspread.authorize(self.credentials)
		spreadsheet = client.open_by_key(self.google_sheet_id)	

		# get list of worksheets
		# sheet = service.spreadsheets().get(spreadsheetId=self.google_sheet_id, ranges=[], includeGridData=False).execute()
		sheets= sheet['sheets']
		
		# define sheetId of the give sheet name
		sheetId = None
		for sheet in sheets:
			properties = sheet['properties']
			if properties['title'] == self.sheet_name:
				sheetId = properties['sheetId']
		
		if sheetId:
			# clear sheet design
			spreadsheet.batch_update({
				"requests": [
					{
						"updateCells": {
							"range": {
								"sheetId": sheetId
							},
							"fields": "userEnteredFormat(textFormat)"
						}
					}
				]
			}
			)
			
			# Add font colour to cell
			if self.cell_colour:
				batch_update_spreadsheet_request_body = {
					"requests": []
				}
				for e in self.cell_colour:
					batch_update_spreadsheet_request_body["requests"].append(
						{
							"repeatCell":
							{
								"range": {
									"sheetId": sheetId,
									"startRowIndex": e["row"],
									"endRowIndex": e["row"]+1,
									"startColumnIndex":e["column"],
									"endColumnIndex": e["column"]+1
								},
								"cell": {
									"userEnteredFormat": {
										"textFormat": {
											"foregroundColor": {
												"red": 1,
												"green": 0,
												"blue":0
											},
											"bold": True
											}
									}
								},
								"fields": "userEnteredFormat(textFormat)"
							}
						}
					)

				request = service.spreadsheets().batchUpdate(spreadsheetId=self.google_sheet_id, body=batch_update_spreadsheet_request_body).execute()
				return request
		return


@frappe.whitelist()
def update_google_sheet_daily():
	list_of_export = frappe.get_list("Google Sheet Data Export",{"enable_auto_update":1}, ['name'])

	for e in list_of_export:
		doc = frappe.get_doc("Google Sheet Data Export",e.name)
		time.sleep(20)

		frappe.enqueue(export_data, 
			doctype= doc.reference_doctype,
			select_columns= doc.field_cache,
			filters= doc.filter_cache,
			with_data = 1,
			link= doc.link,
			google_sheet_id= doc.google_sheet_id,
			sheet_name= doc.sheet_name,
			owner= doc.owner, 
			client_id= doc.client_id,
			is_async=True, queue="long", timeout=6000)

@frappe.whitelist()
def get_client_id():
	SERVICE_ACCOUNT_FILE = os.getcwd()+"/"+cstr(frappe.local.site) + frappe.local.conf.google_sheet
	f = open(SERVICE_ACCOUNT_FILE)
	cred = json.load(f)
	return cred['client_email']

@frappe.whitelist()
def remove_quotes(value):
	if value.startswith('"'):
		value = value[1:]
	if value.endswith('"'):
		value = value[:-1]
	return value
	