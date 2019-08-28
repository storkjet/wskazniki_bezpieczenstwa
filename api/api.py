#-*- coding: utf-8 -*-

from flask import request, Flask, Response
# from flask.ext.api import FlaskAPI

import ujson

from controller.auth import auth
from controller.restService import restService
from controller.filterbox import filterbox

from database import db_session

app = Flask(__name__)
app.register_blueprint(auth)
app.register_blueprint(restService)
app.register_blueprint(filterbox)

@app.route('/')
def hello_world():
	return 'Welcome to WskaznikiBezpieczenstwa-API'

@app.after_request
def setup_cors(response):
	response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
	response.headers['Access-Control-Allow-Credentials'] = 'true'
	response.headers['Access-Control-Allow-Methods'] = 'OPTIONS, GET, POST, PUT, DELETE'
	response.headers['Access-Control-Allow-Headers'] = request.headers.get('Access-Control-Request-Headers', 'Authorization')

	return response

@app.after_request
def remove_db_session(response):
	db_session.remove()

	return response

@app.errorhandler(404)
def not_found(error=None):
	msg = {
		'status': 404,
		'message': 'Not found: %s' % request.url
	}

	return Response(ujson.dumps(msg), mimetype='application/json'), 404

@app.errorhandler(422)
def wrong_parameters(e=None):
	msg = {
		'status': 422,
		'message': 'Wrong request parameters',
		'errors': e
	}

	return Response(ujson.dumps(msg), mimetype='application/json'), 422

if __name__ == '__main__':
	app.run(host='0.0.0.0', debug=True)
	# app.run(debug=False)