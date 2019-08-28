#-*- coding: utf-8 -*-
from flask import Blueprint, request, Response
from sqlalchemy import func, and_
import ujson

from models import InitIdent
from database import db_session
from decorator.auth_decorators import login_required

routes = Blueprint('routes', __name__, url_prefix='/routes')

def get_all_routes():
	results = map(lambda fi: {
				'departure_airport': fi.qar_dep_apt,
				'arrival_airport': fi.qar_arr_apt
			}, db_session.query(InitIdent.qar_dep_apt, InitIdent.qar_arr_apt).distinct(InitIdent.qar_dep_apt, InitIdent.qar_arr_apt).filter(and_(InitIdent.qar_dep_apt != None, InitIdent.qar_arr_apt != None)).order_by(InitIdent.qar_dep_apt.asc()).all())

	return results

def get_top_routes(count=10):
	results = map(lambda fi: {
				'count': fi.count,
				'departure_airport': fi.qar_dep_apt,
				'arrival_airport': fi.qar_arr_apt
			}, db_session.query(func.count(InitIdent.ID).label('count'), InitIdent.qar_dep_apt, InitIdent.qar_arr_apt).filter(and_(InitIdent.qar_dep_apt != None, InitIdent.qar_arr_apt != None)).group_by(InitIdent.qar_dep_apt, InitIdent.qar_arr_apt).order_by('count DESC').limit(count).all())

	return results

@routes.route('/', methods=['GET'])
@login_required()
def get_all():
	if request.method == 'GET':
		results = get_all_routes()
		
		return Response(ujson.dumps(results), mimetype='application/json')

@routes.route('/top', methods=['GET'])
@login_required()
def get_top():
	if request.method == 'GET':
		top_count = request.args.get('count')

		if top_count is None or top_count == '' or int(top_count) < 1:
			top_count = 10
		else:
			top_count = int(top_count)

		results = get_top_routes(top_count)
		
		return Response(ujson.dumps(results), mimetype='application/json')

@routes.route('/all_with_top', methods=['GET'])
@login_required()
def get_all_with_top():
	if request.method == 'GET':
		top_count = request.args.get('count')

		if top_count is None or top_count == '' or int(top_count) < 1:
			top_count = 50
		else:
			top_count = int(top_count)

		results = {
			'all_routes': get_all_routes(),
			'top_routes': get_top_routes(top_count)
		}

		return Response(ujson.dumps(results), mimetype='application/json')