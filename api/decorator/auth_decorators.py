#-*- coding: utf-8 -*-
from functools import update_wrapper
from flask import request, abort
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired, BadSignature

from app_conf import config
from models import User
from helper.role_handler import RoleHandler

def permission_required(permision):
	def decorator(fn):
		def wrapped_function(*args, **kwargs):
			if not 'X-Wskazniki-AuthToken' in request.headers:
				abort(401)

			role_id = verify_auth_token(request.headers.get('X-Wskazniki-AuthToken'))
			handler = RoleHandler()

			if not handler.is_permission_in_role(permision, role_id):
				abort(403)

			return fn(*args, **kwargs)

		return update_wrapper(wrapped_function, fn)

	return decorator

def one_of_permissions_required(permissions):
	def decorator(fn):
		def wrapped_function(*args, **kwargs):
			if not 'X-Wskazniki-AuthToken' in request.headers:
				abort(401)

			role_id = verify_auth_token(request.headers.get('X-Wskazniki-AuthToken'))
			handler = RoleHandler()

			perm_list = [x for x in permissions if handler.is_permission_in_role(x, role_id)]

			if len(perm_list) is 0:
				abort(403)

			return fn(*args, **kwargs)

		return update_wrapper(wrapped_function, fn)

	return decorator

def login_required():
	def decorator(fn):
		def wrapped_function(*args, **kwargs):
			if not 'Authorization' in request.headers:
				abort(401)

			s = Serializer(config['secret_key'])

			try:
				data = s.loads(request.headers.get('Authorization'))
			except SignatureExpired:
				abort(401, 'Session expired. Please log in again.')
			except BadSignature:
				abort(403)

			# TODO check if user exists and is active

			return fn(*args, **kwargs)

		return update_wrapper(wrapped_function, fn)

	return decorator

def get_user_data(request):
	s = Serializer(config['secret_key'])

	try:
		data = s.loads(request.headers.get('Authorization'))
	except SignatureExpired:
		abort(401)
	except BadSignature:
		abort(403)
	
	return data

def verify_auth_token(token):
	s = Serializer(config['secret_key'])

	try:
		data = s.loads(token)
	except SignatureExpired:
		abort(401)
	except BadSignature:
		abort(403)
	
	return data['role']