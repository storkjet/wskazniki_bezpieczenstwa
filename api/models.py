# -*- coding: utf-8 -*-
from sqlalchemy import Column, Integer, String, Date, Time, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship, column_property
from database import Base
from passlib.apps import master_context as pwd_context


class User(Base):
	"""Model for User"""
	__tablename__ = 'auth_user'
	ID = Column('id', Integer, primary_key=True, unique=True)
	password = Column(String(128))
	login = Column('username', String(150), unique=True)
	first_name = Column(String(30))
	last_name = Column(String(30))
	email = Column(String(254))
	is_active = Column(Integer)
	date_joined = Column(DateTime)
	group_id = Column(Integer)

	def __init__(self, login, password, first_name=None, last_name=None, email=None):
		self.login = login
		self.first_name = first_name
		self.last_name = last_name
		self.email = email
		self.hash_password(password)
		self.group_id = 19

	def hash_password(self, plain_password):
		self.password = pwd_context.encrypt(plain_password)

	def verify_password(self, plain_password):
		return pwd_context.verify(plain_password, self.password)

class Role(Base):
	"""Model for Role"""
	__tablename__ = 'web_role'
	ID = Column('id', Integer, primary_key=True, unique=True)
	name = Column(String(200), unique=True)
	alias = Column(String(200), unique=True)

class Privilege(Base):
	"""Model for Privilege"""
	__tablename__ = 'web_privilege'
	ID = Column('id', Integer, primary_key=True, unique=True)
	name = Column(String(200), unique=True)
	alias = Column(String(200), unique=True)

class RoleHasPrivilege(Base):
	"""Model for RoleHasPrivilege"""
	__tablename__ = 'web_role_privilege'
	ID = Column('id', Integer, primary_key=True, unique=True)
	role_id = Column(Integer)
	privilege_id = Column(Integer)

class UserCrewBase(Base):
	"""Model for UserCrewBase"""
	__tablename__ = 'web_user_crew_base'
	ID = Column('id', Integer, primary_key=True, unique=True)
	user_id = Column(Integer, ForeignKey('web_user.id'))
	crew_base = Column(String(10))

class Airport(Base):
	"""Model for Airport"""
	__tablename__ = 'db_airport'
	ID = Column(Integer, primary_key=True)
	airport_icao = Column(String(4), unique=True)
	airport_iata = Column(String(3))
	# crew_base = Column()
	name = Column(String(40))

class InitLanding(Base):
	"""Model for InitLanding"""
	__tablename__ = 'init_landing'
	ID = Column(Integer, primary_key=True)
	reverse = Column(String)
	flaps = Column(Integer)
	acc_ff_1k_ft = Column('accFF_1kFt', Float)
	acc_ff_2k_ft = Column('accFF_2kFt', Float)
	acc_ff_30_nm = Column('accFF_30nm', Float)
	acc_ff_20_nm = Column('accFF_20nm', Float)
	acc_ff_10_nm = Column('accFF_10nm', Float)
	acc_ff_touchdown = Column('accFF_touchdown', Float)
	acc_ff_vacating = Column('accFF_vacating', Float)
	acc_ff_flaps3 = Column('accFF_flap3', Float)
	engine = Column(String)
	user_conf_id = Column('user_conf_ID', Integer)
	comp_reverse = Column(Integer)
	comp_flaps = Column(Integer)
	comp_engine = Column(Integer)
	comp_intersection = Column(Integer)
	comp_all = Column(Integer)
	acc_ff_30_nm_valid = Column('accFF_30nm_valid', Boolean)

class UserConfLanding(Base):
	"""Model for UserConfLanding"""
	__tablename__ = 'user_conf_landing'
	ID = Column('RecordIndex', Integer, primary_key=True)
	airport = Column('Airport', String(4))
	runway = Column('Runway', String(5))
	date_from = Column('DateFrom', Date)
	date_to = Column('DateTo', Date)
	ac_type = Column('ACType', String(10))
	flaps = Column('Flaps', String(10))
	reverse = Column('Reverse', String(10))
	engine = Column('Engine', String(10))
	kpi = Column('KPI', Integer)

	def __init__(self, airport=None, runway=None, date_from=None, date_to=None, ac_type=None, flaps=None, reverse=None, engine=None, kpi=None):
		self.airport = airport
		self.runway = runway
		self.date_from = date_from
		self.date_to = date_to
		self.ac_type = ac_type
		self.flaps = flaps
		self.reverse = reverse
		self.engine = engine
		self.kpi = kpi

class UserConfFlightSpeed(Base):
	"""Model for UserConfFlightSpeed"""
	__tablename__ = 'user_conf_flight_spd'
	ID = Column(Integer, primary_key=True)
	ac_type = Column('ACType', String(10))
	date_from = Column('DateFrom', Date)
	date_to = Column('DateTo', Date)
	ci_climb = Column('CiClimb', Integer)
	ci_cruise = Column('CiCruise', Integer)
	ci_descend = Column('CiDescend', Integer)
	kpi = Column('KPI', Integer)

	def __init__(self, ac_type=None, date_from=None, date_to=None, ci_climb=None, ci_cruise=None, ci_descend=None, kpi=None):
		self.ac_type = ac_type
		self.date_from = date_from
		self.date_to = date_to
		self.ci_climb = ci_climb
		self.ci_cruise = ci_cruise
		self.ci_descend = ci_descend
		self.kpi = kpi


class FDMEvent(Base):
	"""Model for fdm_event"""
	__tablename__ = 'fdm_event'
	id = Column(Integer, primary_key=True)
	session_id = Column(Integer)
	event_type_id = Column(Integer)
	start_id = Column(Integer)
	stop_id = Column(Integer)
	sample = Column(Integer)
	severity = Column(String)
	min_height = Column(Integer)
	assigned_to = Column(Integer)
	status = Column(String)
	importance = Column(String)
	modify_ts = Column(DateTime)
	modify_user = Column(Integer)
	is_visible = Column(Integer)


class FDMEventType(Base):
	"""Model for fdm_event_type"""
	__tablename__ = 'fdm_event_type'
	id = Column(Integer, primary_key=True)
	event_subgroup_id = Column(Integer)
	description = Column('discription', String)
	limit_source = Column(String)
	is_every_second = Column(Integer)


class FDMEventGroup(Base):
	"""Model for fdm_event_group"""
	__tablename__ = 'fdm_event_subgroup'
	id = Column(Integer, primary_key=True)
	event = Column(String)
	event_group_id = Column(Integer)


class DataQarSessionIdent(Base):
	"""Model for data_qar_session_ident"""
	__tablename__ = 'data_qar_session_ident'
	id = Column(Integer, primary_key=True)
	session_id = Column(Integer)
	qar_id = Column(Integer)
	apt_origin = Column(String)
	apt_dest = Column(String)
	block_off = Column(DateTime)
	block_on = Column(DateTime)

class DataQarPhase(Base):
	"""Model for data_qar_session_ident"""
	__tablename__ = 'data_qar_phase'
	id = Column(Integer, primary_key=True)
	PH_id = Column(Integer)
	PH_type = Column(String)
	description = Column(String)


class DataQarFile(Base):
	"""Model for data_qar_file"""
	__tablename__ = 'data_qar_file'
	qar_id = Column(Integer, primary_key=True)
	filename = Column(String)
	ac_id = Column(Integer)
	status = Column(Integer)


class FDMFlightParticipant(Base):
	"""Model for data_qar_file"""
	__tablename__ = 'fdm_flight_participant'
	id = Column(Integer, primary_key=True)
	flight_id = Column(Integer)
	flightlog_flt_id = Column(Integer)


class DataQarFlightIdent(Base):
	"""Model for data_qar_file"""
	__tablename__ = 'data_qar_flight_ident'
	id = Column(Integer, primary_key=True)
	flight_id = Column(Integer)
	session_id = Column(Integer)
	qar_id = Column(Integer)
	apt_dep = Column(String)
	apt_arr = Column(String)
	to_time = Column(DateTime)
	ldg_time = Column(DateTime)
	to_rwy = Column(String)
	ldg_rwy = Column(String)


class ConfFleet(Base):
	"""Model for conf_fleet"""
	__tablename__ = 'conf_fleet'
	id = Column(Integer, primary_key=True)
	ac_reg = Column(String)
	system_uuid = Column(String)
	rec_type = Column(Integer)
	ac_type = Column(Integer)
	operator = Column(Integer)
	alt_gps_offset = Column(Integer)
	sample = Column(Integer)
	is_rpm = Column(Boolean)
	is_cht = Column(Boolean)
	is_mp = Column(Boolean)
	is_oil_t = Column(Boolean)
	is_vol = Column(Boolean)
	is_fuel_p = Column(Boolean)
	is_oil_p = Column(Boolean)
	is_flaps = Column(Boolean)
	is_ff = Column(Boolean)
	is_fqty = Column(Boolean)


class ConfAcType(Base):
	"""Model for conf_ac_type"""
	__tablename__ = 'conf_ac_type'
	id = Column(Integer, primary_key=True)
	factory = Column(String)
	type = Column(String)
	model = Column(String)
	variant = Column(Integer)
	engine_type = Column(String)
	flaps_steps = Column(Integer)
	seats = Column(Integer)
	ceil_max = Column(Integer)
	crz_margin = Column(Integer)
	tg_app = Column(Boolean)
	tg_spd = Column(Boolean)
	tg_min_rpm_spd = Column(Boolean)
	ga_lp_spd = Column(Boolean)
	flaps_full = Column(Boolean)
	flaps_step_2 = Column(Boolean)
	flaps_step_3 = Column(Boolean)
	max_stall_spd = Column(Boolean)
	min_stall_spd = Column(Boolean)
	touchdown_speed = Column(Boolean)
	max_continous_pwr = Column(Integer)
	max_pwr = Column(Integer)
	idle_pwr = Column(Integer)
	modif_ts = Column(DateTime)


class ConfOperator(Base):
	"""Model for conf_operator"""
	__tablename__ = 'conf_operator'
	id = Column(Integer, primary_key=True)
	operator = Column(String)


class FDMEventSort(Base):
	"""Model for fdm_event_sort"""
	__tablename__ = 'fdm_event_group'
	id = Column(Integer, primary_key=True)
	description = Column(String)


class FDMEventDetails(Base):
	"""Model for fdm_event_details"""
	__tablename__ = 'fdm_event_details'
	id = Column(Integer, primary_key=True)
	event_id = Column(Integer)
	param_id = Column(Integer)
	start_value = Column(Float)
	stop_value = Column(Float)
	max = Column(Float)
	min = Column(Float)
	avg = Column(Float)
	var = Column(Float)
	value = Column(Float)


class FDMEventLog(Base):
	"""Model for fdm_event_log"""
	__tablename__ = 'fdm_event_log'
	id = Column(Integer, primary_key=True)
	event_type_id = Column(Integer)
	param_id = Column(Integer)
	is_head = Column(Boolean)
	is_details = Column(Boolean)
	order_nr = Column(Integer)
	is_chart = Column(Boolean)
	is_abs = Column(Integer)


class FDMParam(Base):
	"""Model for fdm_param"""
	__tablename__ = 'fdm_param'
	id = Column(Integer, primary_key=True)
	param_name = Column(String)
	param_name_front = Column(String)
	param_unit = Column(String)
	param_full = Column(String)
	unit_full = Column(String)
	is_primary = Column(Boolean)
	calculations = Column(String)
	is_calculated = Column(Integer)

class ConfAfm(Base):
	"""Model for conf_afm"""
	__tablename__ = 'conf_afm'
	id = Column(Integer, primary_key=True)
	ac_type_id = Column(Integer)
	param_id = Column(Integer)
	event_type_id = Column(Integer)
	caution = Column(Float)
	warning = Column(Float)
	min_sample = Column(Integer)
	sample_type = Column(String)
	yellow = Column(Float)
	red = Column(Float)
	modif_ts = Column(DateTime)
	left_border = Column(Integer)
	right_border = Column(Integer)


class ConfSop(Base):
	"""Model for conf_sop"""
	__tablename__ = 'conf_sop'
	id = Column(Integer, primary_key=True)
	param_id = Column(Integer)
	event_type_id = Column(Integer)
	caution = Column(Float)
	warning = Column(Float)
	min_sample = Column(Integer)
	sample_type = Column(String)
	yellow = Column(Float)
	red = Column(Float)
	modif_ts = Column(DateTime)
	left_border = Column(Integer)
	right_border = Column(Integer)


class FDMParamScale(Base):
	"""Model for fdm_param_scale"""
	__tablename__ = 'fdm_param_scale'
	id = Column(Integer, primary_key=True)
	log_id = Column(Integer)
	limit_type = Column(String)
	is_color_scale = Column(Boolean)
	is_start_value = Column(Boolean)
	is_stop_value = Column(Boolean)
	is_max = Column(Boolean)
	is_min = Column(Boolean)
	is_avg = Column(Boolean)
	is_var = Column(Boolean)
	is_limit = Column(Boolean)
	is_value = Column(Integer)
	is_mirror_reflection = Column(Integer)

class FDMCalculatedEvent(Base):
	"""Model for fdm_calculated_event"""
	__tablename__ = 'fdm_calculated_event'
	id = Column(Integer, primary_key=True)
	data_qar_id = Column(Integer)
	param_id = Column(Integer)
	event_type_id = Column(Integer)
	value = Column(Float)

class CoreAirport(Base):
	"""Model for fdm_param_scale"""
	__tablename__ = 'core_airport'
	id = Column(Integer, primary_key=True)
	name = Column(String)
	icao = Column(String)

class ExportParamName(Base):
	"""Model for export_param_name"""
	__tablename__ = 'export_param_name'
	id = Column(Integer, primary_key=True)
	data_qar_name = Column(String)
	export_name = Column(String)
	param_order = Column(Integer)

class DataQar(Base):
	"""Model for data_qar"""
	__tablename__ = 'data_qar'
	id = Column(Integer, primary_key=True)
	qar_id = Column(Integer)
	recording_id = Column(Integer)
	session_id = Column(Integer)
	mission_id = Column(Integer)
	flight_id = Column(Integer)
	PH = Column(Integer)
	cycle = Column(Integer)
	TS = Column(DateTime)
	LAT = Column(Float)
	LNG = Column(Float)
	ALT_GPS = Column(Integer)
	ALT_STD = Column(Integer)
	ALT_BARO = Column(Integer)
	ALT_DENS = Column(Integer)
	HGT = Column(Integer)
	BARO = Column(Float)
	IAS = Column(Float)
	TAS = Column(Integer)
	GS = Column(Float)
	TRK = Column(Integer)
	HDG_MAG = Column(Integer)
	VAR_MAG = Column(Float)
	WPT = Column(String)
	WPT_DIST = Column(Float)
	WPT_BRG = Column(Integer)
	PITCH = Column(Float)
	ROLL = Column(Float)
	TURN_R = Column(Float)
	AP1 = Column(Integer)
	CRS = Column(Integer)
	CDI_DEV = Column(Float)
	VDI_DEV = Column(Float)
	VS = Column(Integer)
	ACC_LAT = Column(Float)
	ACC_NORM = Column(Float)
	OAT = Column(Integer)
	WD = Column(Integer)
	WS = Column(Integer)
	E1_RPM_1 = Column(Integer)
	E1_RPM_2 = Column(Integer)
	E1_MP = Column(Float)
	E1_FP = Column(Float)
	E1_FF_1 = Column(Float)
	E1_FF_2 = Column(Float)
	FQtyL = Column(Float)
	FQtyR = Column(Float)
	FOB = Column(Float)
	E1_OIL_P = Column(Integer)
	E1_OIL_T = Column(Integer)
	E1_EGT_1 = Column(Integer)
	E1_EGT_2 = Column(Integer)
	E1_EGT_3 = Column(Integer)
	E1_EGT_4 = Column(Integer)
	E1_CHT_1 = Column(Integer)
	E1_CHT_2 = Column(Integer)
	E1_CHT_3 = Column(Integer)
	E1_CHT_4 = Column(Integer)
	E1_VOLT_1 = Column(Float)
	E1_VOLT_2 = Column(Float)
	E1_AMP_1 = Column(Float)
	E1_AMP_2 = Column(Float)
	ELEVT_POS = Column(Integer)
	FLAPS = Column(Integer)


class FrontDataLogging(Base):
	__tablename__="front_data_logging"
	id = Column(Integer, primary_key=True)
	processing_id = Column(Integer)
	operations_nr = Column(Integer)
	events_nr = Column(Integer)
	cautions_nr = Column(Integer)
	warnings_nr = Column(Integer)
	ua_nr = Column(Integer)
	cfit_nr = Column(Integer)
	loc_nr = Column(Integer)
	eo_nr = Column(Integer)
	mac_nr = Column(Integer)
	re_nr = Column(Integer)
	others_nr = Column(Integer)
	ts = Column(DateTime)
	flights_nr = Column(Integer)
	is_notified = Column(Integer)

class DataLogging(Base):
	__tablename__="data_logging"
	id = Column(Integer, primary_key=True)
	processing_id = Column(Integer)
	general_info = Column(String)
	message = Column(String)
	procedure_name = Column(String)
	status = Column(String)
	is_notified = Column(Integer)

class FDMEfsAccess(Base):
	__tablename__="fdm_efs_access"
	id = Column(Integer, primary_key=True)
	efs_user_id = Column(Integer)
	access_granted = Column(Integer)

class FDMSystemUser(Base):
	__tablename__="fdm_system_users"
	id = Column(Integer, primary_key=True)
	email = Column(String)
	is_active = Column(Integer)
	first_name = Column(String)
	last_name = Column(String)
	username = Column(String)

class Flight(Base):
	__tablename__ = "efs_flight"
	flight_id = Column(Integer, primary_key=True)
	trainee_id = Column(Integer)
	instructor_id = Column(Integer)
	training_task_id = Column(Integer)
	training_prog_id = Column(Integer)
	take_off = Column(DateTime)
	landing_on = Column(DateTime)

class FDMEventParticipant(Base):
	__tablename__ = "fdm_event_participant"
	id = Column(Integer, primary_key=True)
	event_id = Column(Integer)
	flightlog_flt_id = Column(Integer)

class EFSUser(Base):
	"""Model for User"""
	__tablename__ = 'efs_auth_user'
	ID = Column('id', Integer, primary_key=True, unique=True)
	first_name = Column(String(30))
	last_name = Column(String(30))
	group_id = Column(Integer)

class FDMMultilimitEvent(Base):
	__tablename__ = 'fdm_multilimit_event'
	id = Column(Integer, primary_key=True)
	data_qar_id = Column(Integer)
	limit_caution = Column(Float)
	limit_warning = Column(Float)
	limit_type = Column(String)
	event_type_id = Column(Integer)

class ConfFDMApi(Base):
	__tablename__ = 'conf_fdm_api'
	id = Column(Integer, primary_key=True)
	property = Column(String)
	value = Column(String)

class Program(Base):
	__tablename__ = 'efs_core_program'
	id = Column(Integer, primary_key=True)
	name = Column(String)
	description = Column(String)

class Task(Base):
	__tablename__ = 'efs_core_task'
	id = Column(Integer, primary_key=True)
	program_id = Column(Integer)
	name = Column(String)
	description = Column(String)