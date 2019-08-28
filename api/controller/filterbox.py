# -*- coding: utf-8 -*-
import time

#from datetime import datetime, timedelta
from flask import Blueprint, request, Response
import ujson
from models import DataQarSessionIdent
from database import db_session
from decorator.auth_decorators import permission_required, login_required

filterbox = Blueprint('filterbox', __name__, url_prefix='/filterbox')

@filterbox.route('/airports', methods=['GET'])
@login_required()
def get_all():
    """
 	Fetch all airports from database.
 	"""
    if request.method == 'GET':
        results = map(lambda fi: {
            'value': fi.apt_origin,
            'label': fi.apt_origin
        }, db_session.query(DataQarSessionIdent.apt_origin).distinct().all())

        # return Response(ujson.dumps(results), content_type='application/json')
        #
        # results = db_session.query(CoreAirport.icao)\
        #                  .all()

        return Response(ujson.dumps(results), mimetype='application/json')

