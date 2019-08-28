#-*- coding: utf-8 -*-
from sqlalchemy import or_

from models import InitIdent

def filter_by_pic(request, q):
	pilot_in_command = request.args.getlist('pic')

	if pilot_in_command is not None and pilot_in_command is not []:
		pics_filter = []

		for p in pilot_in_command:
			pics_filter.append(InitIdent.ofp_cmd_id == p)

		q = q.filter(or_(*pics_filter))

	return q

def filter_by_aircraft_type(request, q):
	aircraft_type = request.args.get('aircraft_type')

	if aircraft_type is not None and aircraft_type != '' and aircraft_type != 'ALL':
		q = q.filter(InitIdent.icao_aircraft_type == aircraft_type)

	return q

def filter_by_crew_base(request, q):
	crew_base = request.args.getlist('crew_base')

	if 'ALL' in crew_base:
		crew_base.remove('ALL')

	if crew_base is not None and crew_base is not []:
		crew_base_filter = []

		for cb in crew_base:
			crew_base_filter.append(InitIdent.crew_base == cb)

		q = q.filter(or_(*crew_base_filter))

	return q

def filter_by_airport(request, q):
	airport = request.args.get('airport')

	if airport is not None and airport != '' and airport != 'ALL':
		q = q.filter(InitIdent.qar_arr_apt == airport)

	return q

def filter_by_runway(request, q):
	airport = request.args.get('airport')
	runway = request.args.get('runway')

	if airport is not None and airport != '' and airport != 'ALL':
		if runway is not None and runway != '' and runway != 'ALL':
			q = q.filter(InitIdent.a_arr_rwy == runway)

	return q