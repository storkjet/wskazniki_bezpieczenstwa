#-*- coding: utf-8 -*-
from flask import Blueprint, request, Response, abort
from sqlalchemy import and_
import ujson

from models import Airport, InitIdent
from database import db_session
from decorator.auth_decorators import permission_required, login_required
from helper import permissions as p

airports = Blueprint('airports', __name__, url_prefix='/airports')

@airports.route('/', methods=['GET'])
@login_required()
def get_all():
	"""
	Fetch all airports from database.
	"""
	if request.method == 'GET':
		limit = request.args.get('limit', 200)
		offset = request.args.get('offset', 0)

		results = map(lambda fi: {
				'airport': fi.qar_arr_apt
			}, db_session.query(InitIdent.qar_arr_apt).distinct(InitIdent.qar_arr_apt).filter(InitIdent.qar_arr_apt != None).order_by(InitIdent.qar_arr_apt.asc()).all())

		return Response(ujson.dumps(results), mimetype='application/json')

@airports.route('/with_runways', methods=['GET'])
@login_required()
def get_with_runways():
	"""
	Fetch all airport with runways (distinct)
	"""
	if request.method == 'GET':
		results = map(lambda fi: {
				'runway': fi.a_arr_rwy,
				'airport': fi.qar_arr_apt
			}, db_session.query(InitIdent.a_arr_rwy, InitIdent.qar_arr_apt).distinct(InitIdent.a_arr_rwy, InitIdent.qar_arr_apt).filter(and_(InitIdent.qar_arr_apt != None, InitIdent.a_arr_rwy != None)).order_by(InitIdent.qar_arr_apt.asc(), InitIdent.a_arr_rwy.asc()).all())

		return Response(ujson.dumps(results), mimetype='application/json')