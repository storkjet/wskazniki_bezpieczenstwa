#-*- coding: utf-8 -*-
from singleton import Singleton
from models import RoleHasPrivilege, Privilege
from database import db_session

class RoleHandler(object):
	__metaclass__ = Singleton

	def __init__(self):
		self.roles_with_permissions = map(lambda r: {
				'role_id': r.role_id,
				'permission_name': r.name
			}, db_session.query(RoleHasPrivilege.role_id, Privilege.name).join(Privilege, Privilege.ID == RoleHasPrivilege.privilege_id).all())

	def is_permission_in_role(self, permission_name, role_id):
		for r in self.roles_with_permissions:
			if r['role_id'] == role_id and r['permission_name'] == permission_name:
				return True

		return False