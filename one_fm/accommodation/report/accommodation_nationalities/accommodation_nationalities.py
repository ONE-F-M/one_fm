# Copyright (c) 2022, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns, data = [], []
	return get_columns(), get_data(filters)

def get_data(filters):
	print(filters)
	conditions = ""
	if filters.accommodation:
		conditions += " WHERE accommodation = %s" % (filters.accommodation)
	results = frappe.db.sql(f"""
		SELECT DISTINCT * FROM `tabBed`
		{conditions}
	""", as_dict=1)

	accommodation_dict = {}
	for row in frappe.db.get_list("Accommodation", fields=['name', 'accommodation']):
		accommodation_dict[row.name] = row.accommodation

	# prepare hashmap
	hashmap = {}
	count = 0
	for row in results:
		if hashmap.get(row.accommodation):
			accommodation = hashmap.get(row.accommodation)
			# CHECK FOR FLOOR
			if accommodation.get(row.floor):
				# CHECK FOR UNIT
				if accommodation[row.floor].get(row.accommodation_unit):
					# CHECK FOR SPACE
					if accommodation[row.floor][row.accommodation_unit].get(row.accommodation_space):
						_space = accommodation[row.floor][row.accommodation_unit][row.accommodation_space]
						if row.nationality:
							if _space.get(row.nationality.lower().replace(' ', '-')):
								_space[row.nationality.lower().replace(' ', '-')] += 1
							else:
								_space[row.nationality.lower().replace(' ', '-')] = 1
							if _space.get('actual'):
								_space['actual'] += 1
							else:
								_space['actual'] = 1
						else:
							if(_space.get('empty')):
								_space['empty'] += 1
							else:
								_space['empty'] = 1

						if(_space.get('total')):
							_space['total'] += 1
						else:
							_space['total'] = 1
						_space['remarks'] = row.gender
						_space['space_type'] = row.accommodation_space_type
					else:
						# NO SPACE
						accommodation[row.floor][row.accommodation_unit][row.accommodation_space] = {
							'type':row.bed_space_type, 'gender':row.gender
						}
						_space = accommodation[row.floor][row.accommodation_unit][row.accommodation_space]
						if (row.nationality):
							if _space.get(row.nationality.lower().replace(' ', '-')):
								_space[row.nationality.lower().replace(' ', '-')] += 1

							else:
								_space[row.nationality.lower().replace(' ', '-')] = 1

							if _space.get('actual'):
								_space['actual'] += 1
							else:
								_space['actual'] = 1

						else:
							if(_space.get('empty')):
								_space['empty'] += 1
							else:
								_space['empty'] = 1

						if(_space.get('total')):
							_space['total'] += 1
						else:
							_space['total'] = 1
						_space['remarks'] = row.gender
						_space['space_type'] = row.accommodation_space_type
				else:
					# NO UNIT
					accommodation[row.floor][row.accommodation_unit] = {
						row.accommodation_space: {'type':row.bed_space_type, 'gender':row.gender},
					}
					_unit = accommodation[row.floor][row.accommodation_unit][row.accommodation_space]
					if (row.nationality):
						if _unit.get(row.nationality.lower().replace(' ', '-')):
							_unit[row.nationality.lower().replace(' ', '-')] += 1

						else:
							_unit[row.nationality.lower().replace(' ', '-')] = 1
						if _unit.get('actual'):
							_unit['actual'] += 1
						else:
							_unit['actual'] = 1
					else:
						if(_unit.get('empty')):
							_unit['empty'] += 1
						else:
							_unit['empty'] = 1
					if(_unit.get('total')):
						_unit['total'] += 1
					else:
						_unit['total'] = 1
					_unit['remarks'] = row.gender
					_unit['space_type'] = row.accommodation_space_type
			else:
				# NO FLOOR
				accommodation[row.floor] = {
					row.accommodation_unit: {
						row.accommodation_space: {'type':row.bed_space_type, 'gender':row.gender},
					}
				}
				_floor = accommodation[row.floor][row.accommodation_unit][row.accommodation_space]
				if (row.nationality):
					if _floor.get(row.nationality.lower().replace(' ', '-')):
						_floor[row.nationality.lower().replace(' ', '-')] += 1

					else:
						_floor[row.nationality.lower().replace(' ', '-')] = 1
					if _floor.get('actual'):
						_floor['actual'] += 1
					else:
						_floor['actual'] = 1
				else:
					if(_floor.get('empty')):
						_floor['empty'] += 1
					else:
						_floor['empty'] = 1

				if(_floor.get('total')):
					_floor['total'] += 1
				else:
					_floor['total'] = 1
				_floor['remarks'] = row.gender
				_floor['space_type'] = row.accommodation_space_type
		else:
			# ADD NEW ACCOMMODATION
			hashmap[row.accommodation] = {
				row.floor: {
					row.accommodation_unit: {
						row.accommodation_space: {'type':row.bed_space_type, 'gender':row.gender},
					}
				}
			}
			_space = hashmap[row.accommodation][row.floor][row.accommodation_unit][row.accommodation_space]
			if (row.nationality):
				_space[row.nationality.lower().replace(' ', '-')] = 1
				_space['actual'] = 1
				_space['empty'] = 0
			else:
				_space['empty'] = 1
				_space['actual'] = 0
			_space['total'] = 1
			_space['gender'] = row.gender
			_space['space_type'] = row.accommodation_space_type

	# structure data
	data = []
	for accommodation, floors in hashmap.items():
		for floor, units in floors.items():
			for unit, spaces in units.items():
				for space, others in spaces.items():
					data.append({**{
						'accommodation': accommodation_dict.get(accommodation),
						'floor': floor,
						'accommodation_unit':unit,
						'room':space,
					}, **others})



	return data

def get_columns():
	return [
			{
				'fieldname': 'accommodation',
				'label': _('Accommodation'),
				'fieldtype': 'Link',
				'options': 'Accommodation',
				'width': 120
			},
			{
				'fieldname': 'floor',
				'label': _('Floor'),
				'fieldtype': 'Link',
				'options': 'Floor',
				'width': 80,
			},
			{
				'fieldname': 'accommodation_unit',
				'label': _('Flat'),
				'fieldtype':'Link',
				'options': 'Accommodation Unit',
				'width': 100,
			},
			{
				'fieldname': 'space_type',
				'label': _('Space Type'),
				'fieldtype': 'Link',
				'width': 100,
				'options': "Accommodation Space Type",
			},
		   {
			   'fieldname': 'room',
			   'label': _('Room'),
			   'fieldtype': 'Link',
			   'width': 100,
			   'options': "Accommodation Space",
		   },
			   {
				   'fieldname': 'gender',
				   'label': _('Gender'),
				   'fieldtype': 'Data',
				   'width': 80,
			   }
		]+ [
			{
				'fieldname': i.nationality.lower().replace(' ', '-'),
				'label': _(i.nationality),
				'fieldtype': 'Link',
				'width': 100,
				'options': 'Nationality'
			} for i in frappe.db.sql("SELECT DISTINCT nationality FROM `tabBed`", as_dict=1) if i.nationality
		]+[
			{
				'fieldname': 'actual',
				'label': _('Occupied'),
				'fieldtype': 'Int',
				'width': 80,
			},
			{
				'fieldname': 'empty',
				'label': _('Empty'),
				'fieldtype': 'Int',
				'width': 80,
			},
			{
				'fieldname': 'total',
				'label': _('Total'),
				'fieldtype': 'Int',
				'width': 80,
			}
		]