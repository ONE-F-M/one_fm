# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext, math, json
from frappe import _
from six import string_types
from frappe.utils import flt, add_months, cint, nowdate, getdate, today, date_diff, month_diff, add_days
from frappe.model.document import Document

class CustomerAsset(Document):
	def validate(self):
		self.validate_asset_values()
		self.validate_item()
		self.prepare_depreciation_data()

	def validate_asset_values(self):
		if not flt(self.gross_purchase_amount):
			frappe.throw(_("Gross Purchase Amount is mandatory"), frappe.MandatoryError)

		if not self.calculate_depreciation:
			return
		elif not self.finance_books:
			frappe.throw(_("Enter depreciation details"))

		if self.available_for_use_date and getdate(self.available_for_use_date) < getdate(self.purchase_date):
				frappe.throw(_("Available-for-use Date should be after purchase date"))

	def validate_item(self):
		item = frappe.get_cached_value("Item", self.item_code,
			["is_stock_item", "disabled"], as_dict=1)
		if not item:
			frappe.throw(_("Item {0} does not exist").format(self.item_code))
		elif item.disabled:
			frappe.throw(_("Item {0} has been disabled").format(self.item_code))
		elif not item.is_stock_item:
			frappe.throw(_("Item {0} must be a stock item").format(self.item_code))
	
	def prepare_depreciation_data(self):
		if self.calculate_depreciation:
			self.value_after_depreciation = 0
			self.set_depreciation_rate()
			self.make_depreciation_schedule()
			self.set_accumulated_depreciation()
		else:
			self.finance_books = []
			self.value_after_depreciation = (flt(self.gross_purchase_amount) -
				flt(self.opening_accumulated_depreciation))
	def set_depreciation_rate(self):
		for d in self.get("finance_books"):
			d.rate_of_depreciation = flt(self.get_depreciation_rate(d, on_validate=True),
			d.precision("rate_of_depreciation"))
	def get_depreciation_rate(self, args, on_validate=False):
		if isinstance(args, string_types):
			args = json.loads(args)

	def make_depreciation_schedule(self):
		if 'Manual' not in [d.depreciation_method for d in self.finance_books]:
			self.schedules = []

		if self.get("schedules") or not self.available_for_use_date:
			return

		for d in self.get('finance_books'):
			self.validate_asset_finance_books(d)

			value_after_depreciation = (flt(self.gross_purchase_amount) -
				flt(self.opening_accumulated_depreciation))

			d.value_after_depreciation = value_after_depreciation

			number_of_pending_depreciations = cint(d.total_number_of_depreciations) - \
				cint(self.number_of_depreciations_booked)

			has_pro_rata = self.check_is_pro_rata(d)

			if has_pro_rata:
				number_of_pending_depreciations += 1

			skip_row = False
			for n in range(number_of_pending_depreciations):
				# If depreciation is already completed (for double declining balance)
				if skip_row: continue

				depreciation_amount = self.get_depreciation_amount(value_after_depreciation,
					d.total_number_of_depreciations, d)

				if not has_pro_rata or n < cint(number_of_pending_depreciations) - 1:
					schedule_date = add_months(d.depreciation_start_date,
						n * cint(d.frequency_of_depreciation))

					# schedule date will be a year later from start date
					# so monthly schedule date is calculated by removing 11 months from it
					monthly_schedule_date = add_months(schedule_date, - d.frequency_of_depreciation + 1)

				# For first row
				if has_pro_rata and n==0:
					depreciation_amount, days, months = get_pro_rata_amt(d, depreciation_amount,
						self.available_for_use_date, d.depreciation_start_date)

					# For first depr schedule date will be the start date
					# so monthly schedule date is calculated by removing month difference between use date and start date
					monthly_schedule_date = add_months(d.depreciation_start_date, - months + 1)

				# For last row
				elif has_pro_rata and n == cint(number_of_pending_depreciations) - 1:
					to_date = add_months(self.available_for_use_date,
						n * cint(d.frequency_of_depreciation))

					depreciation_amount, days, months = get_pro_rata_amt(d,
						depreciation_amount, schedule_date, to_date)

					monthly_schedule_date = add_months(schedule_date, 1)

					schedule_date = add_days(schedule_date, days)
					last_schedule_date = schedule_date

				if not depreciation_amount: continue
				value_after_depreciation -= flt(depreciation_amount,
					self.precision("gross_purchase_amount"))

				# Adjust depreciation amount in the last period based on the expected value after useful life
				if d.expected_value_after_useful_life and ((n == cint(number_of_pending_depreciations) - 1
					and value_after_depreciation != d.expected_value_after_useful_life)
					or value_after_depreciation < d.expected_value_after_useful_life):
					depreciation_amount += (value_after_depreciation - d.expected_value_after_useful_life)
					skip_row = True

				if depreciation_amount > 0:
					# With monthly depreciation, each depreciation is divided by months remaining until next date
					if self.allow_monthly_depreciation:
						# month range is 1 to 12
						# In pro rata case, for first and last depreciation, month range would be different
						month_range = months \
							if (has_pro_rata and n==0) or (has_pro_rata and n == cint(number_of_pending_depreciations) - 1) \
							else d.frequency_of_depreciation

						for r in range(month_range):
							if (has_pro_rata and n == 0):
								# For first entry of monthly depr
								if r == 0:
									days_until_first_depr = date_diff(monthly_schedule_date, self.available_for_use_date)
									per_day_amt = depreciation_amount / days
									depreciation_amount_for_current_month = per_day_amt * days_until_first_depr
									depreciation_amount -= depreciation_amount_for_current_month
									date = monthly_schedule_date
									amount = depreciation_amount_for_current_month
								else:
									date = add_months(monthly_schedule_date, r)
									amount = depreciation_amount / (month_range - 1)
							elif (has_pro_rata and n == cint(number_of_pending_depreciations) - 1) and r == cint(month_range) - 1:
								# For last entry of monthly depr
								date = last_schedule_date
								amount = depreciation_amount / month_range
							else:
								date = add_months(monthly_schedule_date, r)
								amount = depreciation_amount / month_range

							self.append("schedules", {
								"schedule_date": date,
								"depreciation_amount": amount,
								"depreciation_method": d.depreciation_method,
								"finance_book": d.finance_book,
								"finance_book_id": d.idx
							})
					else:
						self.append("schedules", {
							"schedule_date": schedule_date,
							"depreciation_amount": depreciation_amount,
							"depreciation_method": d.depreciation_method,
							"finance_book": d.finance_book,
							"finance_book_id": d.idx
						})

	def validate_asset_finance_books(self, row):
		if flt(row.expected_value_after_useful_life) >= flt(self.gross_purchase_amount):
			frappe.throw(_("Row {0}: Expected Value After Useful Life must be less than Gross Purchase Amount")
				.format(row.idx))

		if not row.depreciation_start_date:
			if not self.available_for_use_date:
				frappe.throw(_("Row {0}: Depreciation Start Date is required").format(row.idx))
			row.depreciation_start_date = self.available_for_use_date

		if not self.is_existing_asset:
			self.opening_accumulated_depreciation = 0
			self.number_of_depreciations_booked = 0
		else:
			depreciable_amount = flt(self.gross_purchase_amount) - flt(row.expected_value_after_useful_life)
			if flt(self.opening_accumulated_depreciation) > depreciable_amount:
					frappe.throw(_("Opening Accumulated Depreciation must be less than equal to {0}")
						.format(depreciable_amount))

			if self.opening_accumulated_depreciation:
				if not self.number_of_depreciations_booked:
					frappe.throw(_("Please set Number of Depreciations Booked"))
			else:
				self.number_of_depreciations_booked = 0

			if cint(self.number_of_depreciations_booked) > cint(row.total_number_of_depreciations):
				frappe.throw(_("Number of Depreciations Booked cannot be greater than Total Number of Depreciations"))

		if row.depreciation_start_date and getdate(row.depreciation_start_date) < getdate(nowdate()):
			frappe.msgprint(_("Depreciation Row {0}: Depreciation Start Date is entered as past date")
				.format(row.idx), title=_('Warning'), indicator='red')

		if row.depreciation_start_date and getdate(row.depreciation_start_date) < getdate(self.purchase_date):
			frappe.throw(_("Depreciation Row {0}: Next Depreciation Date cannot be before Purchase Date")
				.format(row.idx))

		if row.depreciation_start_date and getdate(row.depreciation_start_date) < getdate(self.available_for_use_date):
			frappe.throw(_("Depreciation Row {0}: Next Depreciation Date cannot be before Available-for-use Date")
				.format(row.idx))

	def set_accumulated_depreciation(self, ignore_booked_entry = False):
		straight_line_idx = [d.idx for d in self.get("schedules") if d.depreciation_method == 'Straight Line']
		finance_books = []

		for i, d in enumerate(self.get("schedules")):
			if ignore_booked_entry and d.journal_entry:
				continue

			if d.finance_book_id not in finance_books:
				accumulated_depreciation = flt(self.opening_accumulated_depreciation)
				value_after_depreciation = flt(self.get_value_after_depreciation(d.finance_book_id))
				finance_books.append(d.finance_book_id)

			depreciation_amount = flt(d.depreciation_amount, d.precision("depreciation_amount"))
			value_after_depreciation -= flt(depreciation_amount)

			if straight_line_idx and i == max(straight_line_idx) - 1:
				book = self.get('finance_books')[cint(d.finance_book_id) - 1]
				depreciation_amount += flt(value_after_depreciation -
					flt(book.expected_value_after_useful_life), d.precision("depreciation_amount"))

			d.depreciation_amount = depreciation_amount
			accumulated_depreciation += d.depreciation_amount
			d.accumulated_depreciation_amount = flt(accumulated_depreciation,
				d.precision("accumulated_depreciation_amount"))

	def check_is_pro_rata(self, row):
		has_pro_rata = False

		days = date_diff(row.depreciation_start_date, self.available_for_use_date) + 1
		total_days = get_total_days(row.depreciation_start_date, row.frequency_of_depreciation)

		if days < total_days:
			has_pro_rata = True
		return has_pro_rata

	def get_value_after_depreciation(self, idx):
		return flt(self.get('finance_books')[cint(idx)-1].value_after_depreciation)

	def get_depreciation_amount(self, depreciable_value, total_number_of_depreciations, row):
		precision = self.precision("gross_purchase_amount")

		if row.depreciation_method in ("Straight Line", "Manual"):
			depreciation_left = (cint(row.total_number_of_depreciations) - cint(self.number_of_depreciations_booked))

			if not depreciation_left:
				frappe.msgprint(_("All the depreciations has been booked"))
				depreciation_amount = flt(row.expected_value_after_useful_life)
				return depreciation_amount

			depreciation_amount = (flt(row.value_after_depreciation) -
				flt(row.expected_value_after_useful_life)) / depreciation_left
		else:
			depreciation_amount = flt(depreciable_value * (flt(row.rate_of_depreciation) / 100), precision)

		return depreciation_amount


@frappe.whitelist()
def get_item_details(asset_category):
	asset_category_doc = frappe.get_doc('Asset Category', asset_category)
	books = []
	for d in asset_category_doc.finance_books:
		books.append({
			'finance_book': d.finance_book,
			'depreciation_method': d.depreciation_method,
			'total_number_of_depreciations': d.total_number_of_depreciations,
			'frequency_of_depreciation': d.frequency_of_depreciation,
			'start_date': nowdate()
		})

	return books

def get_pro_rata_amt(row, depreciation_amount, from_date, to_date):
	days = date_diff(to_date, from_date)
	months = month_diff(to_date, from_date)
	total_days = get_total_days(to_date, row.frequency_of_depreciation)

	return (depreciation_amount * flt(days)) / flt(total_days), days, months

def get_total_days(date, frequency):
	period_start_date = add_months(date,
		cint(frequency) * -1)

	return date_diff(date, period_start_date)

def on_purchase_receipt_submit(doc, handler=""):
	for item in doc.items:
		#check item is an asset for customer
		if item.is_customer_asset:
			for qty in range(cint(item.qty)):
				customer_asset_doc = frappe.new_doc('Customer Asset')
				customer_asset_doc.flags.ignore_permissions = True
				customer_asset_doc.asset_name = item.item_name
				customer_asset_doc.item_code = item.item_code
				customer_asset_doc.purchase_receipt = doc.name
				#customer_asset_doc.purchase_invoice = doc.name
				customer_asset_doc.location = 'Cyber pak'
				customer_asset_doc.gross_purchase_amount = item.base_net_rate + item.item_tax_amount
				customer_asset_doc.purchase_date = doc.posting_date
				customer_asset_doc.update({
				'asset_name': customer_asset_doc.asset_name,
				'item_code': customer_asset_doc.item_code,
				'purchase_receipt': customer_asset_doc.purchase_receipt,
				'location': customer_asset_doc.location,
				'gross_purchase_amount': customer_asset_doc.gross_purchase_amount,
				'purchase_date': customer_asset_doc.purchase_date
				}).insert()
			
			frappe.msgprint(msg = 'Customer Assets has been created',
       		title = 'Notification',
      		indicator = 'green'
    		)
