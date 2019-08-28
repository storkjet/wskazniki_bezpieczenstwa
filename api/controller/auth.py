#-*- coding: utf-8 -*-
from flask import Blueprint, request, Response, abort
from datetime import datetime
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
import ujson

from models import User, Role
from database import db_session
from app_conf import config

auth = Blueprint('auth', __name__, url_prefix='/auth')

@auth.route('/login', methods=['POST'])
def login():
	if request.method == 'POST':
		if not request.json:
			abort(400)

		login = request.json.get('login')
		password = request.json.get('password')

		errors = []

		if login is None or login == '':
			errors.append('Login is required')

		if password is None or password == '':
			errors.append('Password is required')

		if len(errors) is not 0:
			abort(422, {'errors': errors})

		u = User.query.filter(User.login == login).first()
		
		if not u or not u.verify_password(password):
			abort(422, {'error': 'Wrong login or password'})

		u.last_logged_in = datetime.now()

		db_session.add(u)
		db_session.commit()
		#TODO: add proper group handling
#		role = Role.query.filter(Role.ID == u.role_id).first()

		result = {
			'first_name': u.first_name,
			'last_name': u.last_name,
			'email': u.email,
#			'role': role.name,
			'auth_token': generate_auth_token(u)
		}

		return Response(ujson.dumps(result), mimetype='application/json')

def generate_auth_token(user):
	s = Serializer(config['secret_key'], expires_in = config['session_duration'])
	return s.dumps({'id': user.ID, 'role': user.group_id})

@auth.route('/register', methods=['POST'])
def register():
	if request.method == 'POST':
		if not request.json:
			abort(400)

		login = request.json.get('login')
		password = request.json.get('password')
		password_confirmation = request.json.get('password_confirmation')
		first_name = request.json.get('first_name')
		last_name = request.json.get('last_name')
		email = request.json.get('email')

		errors = []

		if login is None or login == '':
			errors.append('Login is required')

		if password is None or password == '':
			errors.append('Password is required')

		if password_confirmation is None or password_confirmation == '':
			errors.append('Password  confirmation required')

		if password != password_confirmation:
			errors.append('Passwords does not match')

		if len(errors) is not 0:
			abort(422, {'errors': errors})

		if User.query.filter(User.login == login).first() is not None:
			errors.append('Login is already in use')

		if User.query.filter(User.email == email).first() is not None:
			errors.append('E-mail is already in use')

		if len(errors) is not 0:
			abort(422, {'errors': errors})

		u = User(login, password, first_name, last_name, email)

		db_session.add(u)
		db_session.commit()

		result = {
			'id': u.ID,
			'login': u.login,
			'first_name': u.first_name,
			'last_name': u.last_name,
			'email': u.email
		}

		return Response(ujson.dumps(result), mimetype='application/json'), 201