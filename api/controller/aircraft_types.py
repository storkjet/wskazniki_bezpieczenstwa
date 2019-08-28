#-*- coding: utf-8 -*-
from flask import Blueprint, request, Response
import ujson

from models import InitIdent
from database import db_session
from decorator.auth_decorators import login_required

aircraft_types = Blueprint('aircraft_types', __name__, url_prefix='/aircraft_types')

@aircraft_types.route('/', methods=['GET'])
@login_required()
def get_all():
	if request.method == 'GET':
		limit = request.args.get('limit', 200)
		offset = request.args.get('offset', 0)

		results = map(lambda fi: {
				'aircraft_type': fi.icao_aircraft_type
			}, db_session.query(InitIdent.icao_aircraft_type).distinct(InitIdent.icao_aircraft_type).filter(InitIdent.icao_aircraft_type != None).order_by(InitIdent.icao_aircraft_type.asc()).limit(limit).offset(offset).all())
		
		return Response(ujson.dumps(results), mimetype='application/json')	