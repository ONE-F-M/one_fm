# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and Contributors
# See license.txt
from __future__ import unicode_literals
#test 
import calendar, datetime

import datetime
from dateutil import relativedelta


# import frappe
import unittest

class TestPreRPR(unittest.TestCase):
	pass


# dt = datetime.datetime(year=1998,
#                              month=12,
#                              day=12)
# dt = datetime.date.today()

# nextmonth = dt + relativedelta.relativedelta(months=1)
# nextmonth.replace(day=1)
# print(nextmonth)

#For Returing first date of the next month
# from datetime import date, timedelta
# from calendar import monthrange
# days_in_month = lambda dt: monthrange(dt.year, dt.month)[1]
# today = date.today()
# first_day = today.replace(day=1) + timedelta(days_in_month(today))
# print(first_day)

from datetime import date
from dateutil.relativedelta import relativedelta

today = date.today()
first_day = today.replace(day=1) + relativedelta(months=1)
print(first_day)
# start_date = add_to_date(getdate(), months=-1)
# end_date = get_end_date(start_date, 'monthly')['end_date']
# print(start_date)
# print(end_date)