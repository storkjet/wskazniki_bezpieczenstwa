#-*- coding: utf-8 -*-
from flask import Blueprint, request, Response, abort
from sqlalchemy import func, and_, or_
import ujson

from models import InitIdent, UserCrewBase, User
from database import db_session
from decorator.auth_decorators import login_required, one_of_permissions_required, get_user_data
from utils import get_formated_date
from helper.role_handler import RoleHandler

crew_base = Blueprint('crew_base', __name__, url_prefix='/crew_base')

def filter_by_request(request, q):
	date_from = request.args.get('date_from')
	date_to = request.args.get('date_to')

	if date_from is not None and date_from != '':
		date_from = get_formated_date(date_from)

		q = q.filter(InitIdent.aims_date > date_from)

	if date_to is not None and date_to != '':
		date_to = get_formated_date(date_to)

		q = q.filter(InitIdent.aims_date < date_to)

	return q

@crew_base.route('/', methods=['GET'])
@one_of_permissions_required(['pic_self', 'pic_from_crew_base', 'pic_all'])
def get_all():
	if request.method == 'GET':
		limit = request.args.get('limit', 200)
		offset = request.args.get('offset', 0)

		handler = RoleHandler()
		data = get_user_data(request)

		user = User.query.filter(User.ID == data['id']).first()

		additional_bases = []

		if user is None:
			abort(404, 'User not found')

		if handler.is_permission_in_role('pic_all', data['role']):
			filter_query = and_(*[InitIdent.crew_base != None, InitIdent.crew_base != ''])
			additional_bases.append({ 'crew_base': 'ALL' })

		elif handler.is_permission_in_role('pic_from_crew_base', data['role']):
			results =  map(lambda x: { 'crew_base': x.crew_base }, user.crew_bases)

			return Response(ujson.dumps(results), mimetype='application/json')

		else:
			filter_query = InitIdent.ofp_cmd_id == user.external_id

		db_results = db_session.query(InitIdent.crew_base)\
				.distinct(InitIdent.crew_base).filter(InitIdent.crew_base != None)\
				.filter(filter_query)\
				.order_by(InitIdent.crew_base.asc())\
				.limit(limit)\
				.offset(offset)\
				.all()

		results = map(lambda fi: { 'crew_base': fi.crew_base }, db_results)

		return Response(ujson.dumps(additional_bases + results), mimetype='application/json')

@crew_base.route('/pilot_in_command', methods=['GET'])
@one_of_permissions_required(['pic_self', 'pic_from_crew_base', 'pic_all'])
def get_pilot_in_command():
	if request.method == 'GET':
		handler = RoleHandler()
		data = get_user_data(request)

		user = User.query.filter(User.ID == data['id']).first()

		if user is None:
			abort(404, 'User not found')

		if handler.is_permission_in_role('pic_all', data['role']):
			pic_filter = [InitIdent.ofp_cmd_id != None, InitIdent.crew_base != None]
			filter_query = and_(*pic_filter)

		elif handler.is_permission_in_role('pic_from_crew_base', data['role']):
			crew_bases = map(lambda x: x.crew_base, user.crew_bases)
			pic_filter = [InitIdent.ofp_cmd_id != None, InitIdent.ofp_fo_id != None, InitIdent.crew_base.in_(crew_bases)]
			filter_query = and_(*pic_filter)

		else:
			filter_query = InitIdent.ofp_cmd_id == user.external_id

		q = db_session.query(InitIdent.ofp_cmd_id, InitIdent.ofp_cmd_name, InitIdent.crew_base)\
				.filter(filter_query)\
				.group_by(InitIdent.ofp_cmd_id)\
				.order_by(InitIdent.ofp_cmd_name.asc(), func.count(InitIdent.crew_base).desc())

		q = filter_by_request(request, q)

		results = map(lambda pic: {
				'pic': pic.ofp_cmd_id,
				'name': pic.ofp_cmd_name,
				'crew_base': pic.crew_base
			}, q.all())
		
		return Response(ujson.dumps(results), mimetype='application/json')

