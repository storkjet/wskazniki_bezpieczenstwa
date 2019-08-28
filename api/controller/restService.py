# -*- coding: utf-8 -*-
import time

# from datetime import datetime, timedelta
from flask import Blueprint, request, Response, abort
from sqlalchemy import func, and_, or_
import os
import math
import ujson
import logging
from datetime import datetime
from models import FDMEvent, FDMEventType, FDMEventGroup, DataQarSessionIdent, DataQarFile, ConfFleet, ConfAcType
from models import ConfOperator, FDMEventSort, FDMEventDetails, FDMEventLog, FDMParam, ConfAfm, ConfSop, FDMParamScale
from models import DataQar, User, FrontDataLogging, ConfFDMApi, Flight, FDMEventParticipant, EFSUser, FDMMultilimitEvent, DataQarPhase
from models import Program, Task, CoreAirport, FDMCalculatedEvent, DataQarFlightIdent, FDMFlightParticipant, ExportParamName, FDMSystemUser
from database import db_session
from sqlalchemy.orm import aliased
from decorator.auth_decorators import permission_required, login_required, get_user_data
from utils import get_int_or_none
import datetime
import sys
import smtplib
import dns.resolver
from threading import Timer, Thread
import time
import random
from os import environ

reload(sys)
sys.setdefaultencoding("utf-8")
import codecs

from collections import OrderedDict

restService = Blueprint('restService', __name__, url_prefix='/api')
logger = logging.getLogger('WskaznikiBezpieczenstwa')
hdlr = logging.FileHandler('.\page-access.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)
logger.info("Logger started...")

def sendmail(FROM = '', SUBJECT = 'Hi'):
    TO = []
    final_results = []
    results = map(lambda fi: {
        'email': fi.email,
    }, db_session.query(User.email)
                  .filter(User.is_active == 1)
                  .all())
    for i in results:
        TO.append(i['email'])

    print "New event's found. \nSending mail to client"

    TEXT = 'Hi \nNew event''s appear'
    print TO
    TO = ['']
    #message = "From: %s\nTo: %s\nSubject: %s\n\n%s" % (FROM, TO, SUBJECT, TEXT)
    for i in TO:
        message = "From: %s\nTo: %s\nSubject: %s\n\n%s" % (FROM, i, SUBJECT, TEXT)
        domain = i.split('@')[1]
        mx = str(dns.resolver.query(domain, 'MX')[0].exchange)
        server = smtplib.SMTP(mx)
        server.sendmail(FROM, i, message)
        server.quit()

def checkIncidents(intervall = 10):
    while True:
        time.sleep(float(environ['NEW_INCIDENTS_CHECK_INTERVALL']))
        results = map(lambda fi: {
            'events_nr': fi.events_nr,
        }, db_session.query(FrontDataLogging.events_nr)
                      .filter(FrontDataLogging.is_notified == -1)
                      .all())

        for i in results:
            if i['events_nr'] > 0:
                repeat = True;
                while repeat == True:
                    e = None
                    e = FrontDataLogging.query.filter(FrontDataLogging.is_notified == -1).first()
                    if e == None:
                        repeat = False
                        break;

                    e.is_notified = 0

                    try:
                        db_session.add(e)
                        db_session.commit()

                    except:
                        abort(400)

                sendmail()
                break;


@restService.route('/users', methods=['GET'])
@login_required()
def get_users():
    if request.method == 'GET':
        user = request.args.get('user')

        logger.info("[%s][Specific Range]",
                     user)

        results = map(lambda fi: {
                'value': fi.ID,
                'label': fi.first_name + ' ' + fi.last_name,
             }, db_session.query(User.ID, User.first_name, User.last_name)
                         .all())

        return Response(ujson.dumps(results), mimetype='application/json')

@restService.route('/event_list', methods=['GET'])
@login_required()
def get_all_events():

    """
 	Fetch all event list from database.
 	"""
    if request.method == 'GET':
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        user = request.args.get('user')
        temparray = request.args.get('events_id')
        temparray1 = request.args.get('programs_id')
        events_id = ProcessData(temparray) #Transform data
        programs_id = ProcessData(temparray1)  # Transform data
        assigned_to = request.args.get('assigned_to')
        status = request.args.get('status')
        importance = request.args.get('importance')
        event_with_program = request.args.get('event_with_program')
        logger.info("[%s][Specific Range] DateFrom: %s, DateTo: %s,",
                     user, date_from, date_to)
        is_efs = is_efs_connected().response[0]

        cau = aliased(FDMEvent)
        war = aliased(FDMEvent)

        baked_query = db_session.query(FDMEvent.session_id, ConfAcType.model, ConfFleet.ac_reg, DataQarSessionIdent.apt_origin,
                                DataQarSessionIdent.apt_dest, DataQarSessionIdent.block_off,
                                DataQarSessionIdent.block_on, func.count(cau.id).label('cautions'), func.count(war.id).label('warnings'))\
                       .outerjoin(DataQarSessionIdent, FDMEvent.session_id == DataQarSessionIdent.session_id)\
                       .outerjoin(DataQarFile, DataQarSessionIdent.qar_id == DataQarFile.qar_id)\
                       .outerjoin(ConfFleet, DataQarFile.ac_id == ConfFleet.id)\
                       .outerjoin(ConfAcType, ConfFleet.ac_type == ConfAcType.id)\
                       .outerjoin(cau, and_(FDMEvent.id == cau.id, cau.severity == 'caution'))\
                       .outerjoin(war, and_(FDMEvent.id == war.id, war.severity == 'warning')) \
                       .group_by(FDMEvent.session_id)

        if event_with_program == 0 or event_with_program == "0":
            baked_query = baked_query.join(FDMEventParticipant, FDMEvent.id == FDMEventParticipant.event_id)
            baked_query = baked_query.outerjoin(Flight, Flight.flight_id == FDMEventParticipant.flightlog_flt_id)
        else:
            baked_query = baked_query.outerjoin(FDMEventParticipant, FDMEvent.id == FDMEventParticipant.event_id)
            baked_query = baked_query.outerjoin(Flight, Flight.flight_id == FDMEventParticipant.flightlog_flt_id)

        if date_from != 'null':
            baked_query = baked_query.filter(DataQarSessionIdent.block_off > date_from)

        if date_to != 'null':
            baked_query = baked_query.filter(DataQarSessionIdent.block_off < date_to)

        if assigned_to != 'null' and assigned_to != 'all':
            baked_query = baked_query.filter(FDMEvent.assigned_to == assigned_to)

        if assigned_to == 'null':
            baked_query = baked_query.filter(FDMEvent.assigned_to == None)

        if status != 'null' and status != 'all':
            baked_query = baked_query.filter(FDMEvent.status == status)

        if status == 'null':
            baked_query = baked_query.filter(FDMEvent.status == None)

        if importance != 'null' and importance != 'all':
            baked_query = baked_query.filter(FDMEvent.importance == importance)

        if importance == 'null':
            baked_query = baked_query.filter(FDMEvent.importance == None)

        if len(events_id) > 0 and events_id[0] != 0:
            baked_query = baked_query.filter(FDMEvent.event_type_id.in_(events_id))
        if events_id == []:
            baked_query = baked_query.filter(FDMEvent.event_type_id.in_(events_id))

        if len(programs_id) > 0 and programs_id[0] != 0:
            baked_query = baked_query.filter(or_(Flight.training_task_id.in_(programs_id), FDMEventParticipant.flightlog_flt_id == None))
        elif programs_id == []:
            baked_query = baked_query.filter(or_(Flight.training_task_id.in_(programs_id), FDMEventParticipant.flightlog_flt_id == None))
        else:
            baked_query = baked_query.filter(or_(Flight.training_task_id.in_([]), FDMEventParticipant.flightlog_flt_id == None))

        sta = aliased(DataQar)
        sto = aliased(DataQar)

        results = map(lambda fi:{
            'session_id': fi.session_id,
            'ac_type': fi.model,
            'ac_reg': fi.ac_reg,
            'airport_departure': fi.apt_origin,
            'airport_arrival': fi.apt_dest,
            'block_off': fi.block_off,
            'block_on': fi.block_on,
            'cautions': fi.cautions,
            'warnings': fi.warnings,
            'events': map(lambda gi:{
                    'event_id': gi.id,
                    'event_group': gi.event_group,
                    'event_subgroup': gi.event,
                    'event_type': gi.description,
                    'event_start': gi.start,
                    'event_end': gi.end,
                    'severity': gi.severity,
                    'assigned_to': gi.assigned_to,
                    'status': gi.status,
                    'importance': gi.importance
                    }, db_session.query(FDMEvent.id, FDMEventSort.description.label('event_group'), FDMEventGroup.event,
                                        FDMEventType.description, sta.TS.label('start'), sto.TS.label('end'), FDMEvent.severity,
                                        (User.first_name + ' ' + User.last_name).label('assigned_to'), FDMEvent.status, FDMEvent.importance)
                                .outerjoin(FDMEventType, FDMEvent.event_type_id == FDMEventType.id)
                                .outerjoin(FDMEventGroup, FDMEventType.event_subgroup_id == FDMEventGroup.id)
                                .outerjoin(FDMEventSort, FDMEventGroup.event_group_id == FDMEventSort.id)
                                .outerjoin(sta, FDMEvent.start_id == sta.id)
                                .outerjoin(sto, FDMEvent.stop_id == sto.id)
                                .outerjoin(User, FDMEvent.assigned_to == User.ID)
                                .filter(FDMEvent.session_id == fi.session_id, FDMEvent.is_visible == 1)
                                .all()
                )
            }, baked_query.all()
        )

        for entity in results:
            c = 0
            w = 0
            for event in entity['events']:
                if event['severity'] == 'caution':
                    c = c + 1
                else:
                    w = w + 1
            entity['cautions'] = c
            entity['warnings'] = w

        return Response(ujson.dumps(results), mimetype='application/json')


@restService.route('/event_details/bars', methods=['GET'])
@login_required()
def get_event_details_bars():
    """
 	Fetch details of details.
 	"""
    if request.method == 'GET':
        event_id = request.args.get('event_id')
        user = request.args.get('user')

        logger.info("[%s][Event Details] Event Id: %s",
                    user, event_id)

        event_id = get_int_or_none(event_id)

        results = map(lambda fi: {
            'param_name': fi.param_name,
            'param_unit': fi.param_unit,
            'param_full': fi.param_full,
            'unit_full': fi.unit_full,
            'start': fi.start,
            'stop': fi.stop,
            'max': fi.max,
            'min': fi.min,
            'avg': fi.avg,
            'var': fi.var,
            'caution_limit': fi.caution_limit,
            'warning_limit': fi.warning_limit,
            'limit_type': fi.limit_type,
            'left_border': fi.left_border,
            'right_border': fi.right_border,
            'value': fi.value,
        }, db_session.query(FDMEvent.id, FDMParam.param_name, FDMParam.param_unit, FDMParam.param_full,
                            FDMParam.unit_full, func.IF(FDMParamScale.is_start_value, FDMEventDetails.start_value, None).label('start'),
                            func.IF(FDMParamScale.is_stop_value, FDMEventDetails.stop_value, None).label('stop'),
                            func.IF(FDMParamScale.is_max, FDMEventDetails.max, None).label('max'),
                            func.IF(FDMParamScale.is_min, FDMEventDetails.min, None).label('min'),
                            func.IF(FDMParamScale.is_avg, FDMEventDetails.avg, None).label('avg'),
                            func.IF(FDMParamScale.is_var, FDMEventDetails.var, None).label('var'),
                            func.IF(FDMParamScale.is_value, FDMEventDetails.value, None).label('value'),
                            func.coalesce(ConfAfm.caution, ConfSop.caution).label('caution_limit'),
                            func.coalesce(ConfAfm.warning, ConfSop.warning).label('warning_limit'),
                            func.coalesce(ConfAfm.left_border, ConfSop.left_border).label('left_border'),
                            func.coalesce(ConfAfm.right_border, ConfSop.right_border).label('right_border'),
                            FDMParamScale.limit_type,
                            FDMEventDetails.value)
                      .join(FDMEventType, FDMEventType.id == FDMEvent.event_type_id)
                      .join(DataQarSessionIdent, DataQarSessionIdent.session_id == FDMEvent.session_id)
                      .join(DataQarFile, DataQarFile.qar_id == DataQarSessionIdent.qar_id)
                      .join(ConfFleet, ConfFleet.id == DataQarFile.ac_id)
                      .join(FDMEventDetails, FDMEventDetails.event_id == FDMEvent.id)
                      .join(FDMEventLog, and_(FDMEventLog.event_type_id == FDMEvent.event_type_id,
                                              FDMEventLog.param_id == FDMEventDetails.param_id))
                      .join(FDMParam, FDMParam.id == FDMEventLog.param_id)
                      .outerjoin(ConfAfm, and_(ConfAfm.event_type_id == FDMEvent.event_type_id,
                                               ConfAfm.param_id == FDMEventDetails.param_id,
                                               ConfAfm.ac_type_id == ConfFleet.ac_type,
                                               FDMEventType.limit_source == 'afm'))
                      .outerjoin(ConfSop, and_(ConfSop.event_type_id == FDMEvent.event_type_id,
                                               ConfSop.param_id == FDMEventDetails.param_id,
                                               FDMEventType.limit_source == 'sop'))
                      .join(FDMParamScale, FDMParamScale.log_id == FDMEventLog.id)
                      .filter(FDMEventLog.is_head == True, FDMEvent.id == event_id)
                      .all())

        return Response(ujson.dumps(results), mimetype='application/json')

@restService.route('/event_group', methods=['GET'])
@login_required()
def get_groups():
    if request.method == 'GET':
        user = request.args.get('user')

        logger.info("[%s][Specific Range]",
                     user)

        results = map(lambda fi: {
                'event_group_id': fi.id,
                'label': fi.description,
                'value': fi.description,
                'children': map(lambda gi: {
                    'event_subgroup_id': gi.id,
                    'label': gi.event,
                    'children': map(lambda hi: {
                        'event_type_id': hi.id,
                        'label': hi.description,
                     }, db_session.query(FDMEventType.description, FDMEventType.id)
                                 .filter(FDMEventType.event_subgroup_id == gi.id)
                                 .all()),
                 }, db_session.query(FDMEventGroup.event, FDMEventGroup.id)
                             .filter(FDMEventGroup.event_group_id == fi.id)
                             .all()),
             }, db_session.query(FDMEventSort.description, FDMEventSort.id)
                         .all())

        return Response(ujson.dumps(results), mimetype='application/json')

@restService.route('/programs', methods=['GET'])
@login_required()
def get_programs():
    if request.method == 'GET':
        user = request.args.get('user')

        logger.info("[%s][Specific Range]",
                     user)

        results = map(lambda fi: {
                'program_id': fi.id,
                'label': fi.name,
                'value': fi.name,
                'description': fi.description,
                'children': map(lambda gi: {
                    'task_id': gi.id,
                    'description': gi.description,
                    'label': gi.name
                 }, db_session.query(Task.name, Task.id, Task.description)
                             .filter(Task.program_id == fi.id)
                             .all()),
             }, db_session.query(Program.description, Program.id, Program.name)
                         .all())

        return Response(ujson.dumps(results), mimetype='application/json')

def ProcessData(arr):
    if ((len(arr) != 0) and ('u' not in arr) and ('N' not in arr)):
        x = ''
        idarray = []
        if arr == u'Nan':
            return idarray
        for num in arr:
            if (num != ','):
                x += str(num)
            else:
                idarray.append(int(x))
                x = ''
        idarray.append(int(x))
        final_list = idarray
        return final_list

    elif ((len(arr) != 0) and 'u' in arr) or ((len(arr) != 0) and 'N' in arr):
        return [-1]
    else:
        return []

    return Response(ujson.dumps(results), mimetype='application/json')

def valueSwitch(x, table, alt_offset, war_ias, cau_ias):
    return {
        'TS': table.TS,
        'GS': table.GS,
        'IAS': table.IAS,
        'FLAPS': table.FLAPS,
        'E1_OIL_T': table.E1_OIL_T,
        'ROLL': table.ROLL,
        'PITCH': table.PITCH,
        'ALT_GPS': table.ALT_GPS,
        'VS': table.VS,
        'E1_RPM_1': table.E1_RPM_1,
        'ACC_NORM': table.ACC_NORM,
        'E1_VOLT_1': table.E1_VOLT_1,
        'E1_AMP_1': table.E1_AMP_1,
        'E1_OIL_P': table.E1_OIL_P,
        'E1_FP': table.E1_FP,
        'E1_CHT_1': table.E1_CHT_1,
        'E1_CHT_2': table.E1_CHT_2,
        'E1_CHT_3': table.E1_CHT_3,
        'E1_CHT_4': table.E1_CHT_4,
        'TRK': table.TRK,
        'HDG_MAG': table.HDG_MAG,
        'FQtyL': table.FQtyL,
        'FQtyR': table.FQtyR,
        'E1_FF_1': table.E1_FF_1,
        'HGT': table.HGT,
        'ALT_BARO': table.ALT_BARO,
        'BARO': table.BARO,
        'gradient': table.VS/table.GS,
        'tailwind': table.GS - (table.IAS * (1 + (table.ALT_GPS/1000 * 0.02))),
        'time':  table.TS,
        'crosswind': (((table.GS * func.SIN(func.RADIANS(func.IF(func.ABS(table.TRK - table.HDG_MAG) > 180, func.ABS(360 - func.ABS(table.TRK - table.HDG_MAG)),func.ABS(table.TRK - table.HDG_MAG))))) / (func.SQRT(func.POW((table.IAS * (1 + (table.ALT_GPS/1000 * 0.02))),2) + func.POW(table.GS,2) - 2*(table.IAS * (1 + (table.ALT_GPS/1000 * 0.02)))*table.GS*func.COS(func.RADIANS(func.IF(func.ABS(table.TRK - table.HDG_MAG) > 180, func.ABS(360 - func.ABS(table.TRK - table.HDG_MAG)), func.ABS(table.TRK - table.HDG_MAG))))))) * (func.SQRT(func.POW((table.IAS * (1 + (table.ALT_GPS/1000 * 0.02))),2) + func.POW(table.GS,2) - 2*(table.IAS * (1 + (table.ALT_GPS/1000 * 0.02)))*table.GS*func.COS(func.RADIANS(func.IF(func.ABS(table.TRK - table.HDG_MAG) > 180, func.ABS(360 - func.ABS(table.TRK - table.HDG_MAG)), func.ABS(table.TRK - table.HDG_MAG))))))),
        'vs_to_hgt': table.VS/(table.HGT - alt_offset),
        'roll_to_hgt': table.ROLL/(table.HGT - alt_offset),
        'elev': table.ALT_GPS - (table.HGT - alt_offset),
        # 'duration': ,
        # 'lost_fuel': ,
        # 'lndg_dist': ,
        # 'trk_var': ,
        # 'runup_duration': ,
        # 'fuel_endurance': ,
        # 'elev_rate': ,
        'alt_dev': func.ABS(table.ALT_GPS - table.ALT_BARO),
        'fuel_diff': func.ABS(table.FQtyL - table.FQtyR),
        # 'end_of_rwy': ,
        # 'nearest_ad': ,
        # 'tcr_to_hgt': ,
        'caution_ias': FDMMultilimitEvent.limit_caution,
        'warning_ias': FDMMultilimitEvent.limit_warning,
        # 'spd_to_dist_ratio': ,
        'hgt_corr': table.HGT - alt_offset,
        'cycle': table.cycle
    }.get(x)

@restService.route('/event_details/chart', methods=['GET'])
@login_required()
def get_event_details_chart():
    """
 	Fetch details of details.
 	"""
    if request.method == 'GET':
        event_id = request.args.get('event_id')
        user = request.args.get('user')

        logger.info("[%s][Event Details] Event Id: %s",
                    user, event_id)
        event_id = get_int_or_none(event_id)

        results = db_session.query(FDMEvent.id, FDMParam.param_name, FDMParam.is_primary, FDMParam.calculations,
                                   FDMParamScale.is_color_scale, FDMParamScale.limit_type, FDMEvent.start_id,
                                   FDMEvent.stop_id, FDMEventDetails.min, FDMEventDetails.max,
                                   func.coalesce(ConfAfm.caution, ConfSop.caution).label('caution_limit'),
                                   func.coalesce(ConfAfm.warning, ConfSop.warning).label('warning_limit'),
                                   ConfFleet.alt_gps_offset, FDMEventLog.is_chart, FDMMultilimitEvent.limit_warning, FDMMultilimitEvent.limit_caution,
                                   func.IF(FDMParamScale.is_max == 0, 1, 2).label('critical_value'),
                                   FDMParam.param_name_front, FDMParam.param_full, FDMParam.param_unit, FDMEventType.is_every_second,
                                   FDMParamScale.is_mirror_reflection, FDMEvent.event_type_id, FDMEventLog.is_abs, FDMParam.is_calculated, FDMParam.id )\
                            .join(FDMEventLog, FDMEvent.event_type_id == FDMEventLog.event_type_id)\
                            .join(FDMParam, FDMEventLog.param_id == FDMParam.id)\
                            .join(FDMEventType, FDMEventType.id == FDMEvent.event_type_id)\
                            .join(DataQarSessionIdent, DataQarSessionIdent.session_id == FDMEvent.session_id)\
                            .join(DataQarFile, DataQarFile.qar_id == DataQarSessionIdent.qar_id) \
                            .join(ConfFleet, ConfFleet.id == DataQarFile.ac_id)\
                            .outerjoin(FDMParamScale, FDMEventLog.id == FDMParamScale.log_id) \
                            .outerjoin(FDMEventDetails, and_(FDMEventDetails.event_id == FDMEvent.id,
                                                        FDMEventDetails.param_id == FDMEventLog.param_id)) \
                            .outerjoin(ConfAfm, and_(ConfAfm.event_type_id == FDMEvent.event_type_id,
                                                     ConfAfm.param_id == FDMEventDetails.param_id,
                                                     ConfAfm.ac_type_id == ConfFleet.ac_type,
                                                     FDMEventType.limit_source == 'afm'))\
                            .outerjoin(ConfSop, and_(ConfSop.event_type_id == FDMEvent.event_type_id,
                                                     ConfSop.param_id == FDMEventDetails.param_id,
                                                     FDMEventType.limit_source == 'sop'))\
                            .outerjoin(FDMMultilimitEvent, FDMEvent.start_id == FDMMultilimitEvent.data_qar_id)\
                            .filter(FDMEvent.id == event_id)\
                            .order_by(FDMEventLog.order_nr).all()

        baked_query = db_session.query(DataQar.cycle, DataQar.TS).outerjoin(FDMMultilimitEvent, FDMMultilimitEvent.data_qar_id == DataQar.id)
        headers = ['id']
        results2 = []
        coloring_data = []
        for entity in results:
            #Map to DB column
            """
            0 - event id
            1 - column name
            2 - if column is primary
            3 - does it need special calculation
            4 - is color scaled
            5 - which way to color
            6 - start_id
            7 - stop_id
            8 - min
            9 - max
            10 - caution limit
            11 - warning limit
            12 - alt offset
            13 - is in chart
            14 - multilimit warning
            15 - multilimit caution
            16 - is max value
            17 - param front name
            18 - param description
            19 - param unit
            20 - is second
            21 - mirror reflection
            22 - event type id
            23 - is abs
            24 - is calculated
            25 - Param id
            """
            if entity[13]:
                if entity[24] != 1:
                    baked_query = baked_query.add_columns(valueSwitch(entity[1], DataQar, entity[12], entity[14], entity[15]))
                    h = {
                        'name': entity[1],
                        'front_name': entity[17],
                        'full_name': entity[18],
                        'param_unit': entity[19],
                        'is_second': entity[20],
                        'caution_limit': entity[10],
                        'warning_limit': entity[11],
                        'is_mirror_reflection': entity[21],
                        'is_chart': entity[13],
                        'event_type_id': entity[22],
                        'is_abs': entity[23],
                        'is_calculated': entity[24]
                    }
                    headers.append(h)
                else:
                    baked_query = db_session.query(DataQar.cycle, DataQar.TS, FDMCalculatedEvent.value).filter(FDMCalculatedEvent.data_qar_id == DataQar.id)    \
                    .filter(FDMCalculatedEvent.param_id == entity[25])
                    h = {
                        'name': entity[1],
                        'front_name': entity[17],
                        'full_name': entity[18],
                        'param_unit': entity[19],
                        'is_second': entity[20],
                        'caution_limit': entity[10],
                        'warning_limit': entity[11],
                        'is_mirror_reflection': entity[21],
                        'is_chart': entity[13],
                        'event_type_id': entity[22],
                        'is_abs': entity[23],
                        'is_calculated': entity[24]
                    }
                    headers.append(h)

        results = baked_query.filter(DataQar.id >= results[0][6], DataQar.id <= results[0][7]).order_by(DataQar.id).all()
        results2.append(tuple(headers))
        for item in results:
            results2.append(item)

        final_results = []
        final_results.append(results2)

        results3 = db_session.query(FDMMultilimitEvent.limit_warning, FDMMultilimitEvent.limit_caution,
                                    FDMMultilimitEvent.limit_type, DataQar.TS, FDMMultilimitEvent.event_type_id) \
            .filter(and_(FDMEvent.start_id <= FDMMultilimitEvent.data_qar_id,
                                                FDMEvent.stop_id >= FDMMultilimitEvent.data_qar_id)) \
            .filter(FDMEvent.id == event_id) \
            .filter(FDMMultilimitEvent.data_qar_id == DataQar.id) \

        final_results.append(results3)


        return Response(ujson.dumps(final_results), mimetype='application/json')


@restService.route('/event_details/table', methods=['GET'])
@login_required()
def get_event_details_table():

    """
 	Fetch details of details.
 	"""
    if request.method == 'GET':
        event_id = request.args.get('event_id')
        user = request.args.get('user')

        logger.info("[%s][Event Details] Event Id: %s",
                    user, event_id)
        event_id = get_int_or_none(event_id)
        results = db_session.query(FDMEvent.id, FDMParam.param_name, FDMParam.is_primary, FDMParam.calculations,
                                   FDMParamScale.is_color_scale, FDMParamScale.limit_type, FDMEvent.start_id,
                                   FDMEvent.stop_id, FDMEventDetails.min, FDMEventDetails.max,
                                   func.coalesce(ConfAfm.caution, ConfSop.caution).label('caution_limit'),
                                   func.coalesce(ConfAfm.warning, ConfSop.warning).label('warning_limit'),
                                   ConfFleet.alt_gps_offset, FDMEventLog.is_details, FDMMultilimitEvent.limit_warning, FDMMultilimitEvent.limit_caution,
                                   func.IF(FDMParamScale.is_max == 0, 1, 2).label('critical_value'),
                                   FDMParam.param_name_front, FDMParam.param_full, FDMParam.param_unit, FDMEventType.is_every_second, FDMParam.is_calculated, FDMEventLog.is_abs, FDMEvent.session_id, FDMParamScale.id, ConfFleet.rec_type)\
                            .join(FDMEventLog, FDMEvent.event_type_id == FDMEventLog.event_type_id)\
                            .join(FDMParam, FDMEventLog.param_id == FDMParam.id)\
                            .join(FDMEventType, FDMEventType.id == FDMEvent.event_type_id)\
                            .join(DataQarSessionIdent, DataQarSessionIdent.session_id == FDMEvent.session_id)\
                            .join(DataQarFile, DataQarFile.qar_id == DataQarSessionIdent.qar_id) \
                            .join(ConfFleet, ConfFleet.id == DataQarFile.ac_id)\
                            .outerjoin(FDMParamScale, FDMEventLog.id == FDMParamScale.log_id) \
                            .outerjoin(FDMEventDetails, and_(FDMEventDetails.event_id == FDMEvent.id,
                                                        FDMEventDetails.param_id == FDMEventLog.param_id)) \
                            .outerjoin(ConfAfm, and_(ConfAfm.event_type_id == FDMEvent.event_type_id,
                                                     ConfAfm.param_id == FDMEventDetails.param_id,
                                                     ConfAfm.ac_type_id == ConfFleet.ac_type,
                                                     FDMEventType.limit_source == 'afm'))\
                            .outerjoin(ConfSop, and_(ConfSop.event_type_id == FDMEvent.event_type_id,
                                                     ConfSop.param_id == FDMEventDetails.param_id,
                                                     FDMEventType.limit_source == 'sop'))\
                            .outerjoin(FDMMultilimitEvent, FDMEvent.start_id == FDMMultilimitEvent.data_qar_id)\
                            .filter(FDMEvent.id == event_id)\
                            .order_by(FDMEventLog.order_nr).all()

        baked_query = db_session.query(DataQar.id).outerjoin(FDMMultilimitEvent, FDMMultilimitEvent.data_qar_id == DataQar.id)
        headers = ['id']
        results2 = []
        coloring_data = []
        for entity in results:
            #Map to DB column
            #array desc:
            """
            0 - event id
            1 - column name
            2 - if column is primary
            3 - does it need special calculation
            4 - is color scaled
            5 - which way to color
            6 - start_id
            7 - stop_id
            8 - min
            9 - max
            10 - caution limit
            11 - warning limit
            12 - alt offset
            13 - is in table
            14 - multilimit warning
            15 - multilimit caution
            16 - is max value
            17 - param front name
            18 - param description
            19 - param unit
            20 - is second
            21 - is calculated
            22 - is abs
            23 - event session id
            24 - paramscale id
            25 - rec type
            26 - phase desc
            """
            if entity[13]:
                if entity[21] != 1:
                    baked_query = baked_query.add_columns(valueSwitch(entity[1], DataQar, entity[12], entity[14], entity[15]) )
                    h = {
                        'name': entity[1],
                        'front_name': entity[17],
                        'full_name': entity[18],
                        'param_unit': entity[19],
                        'is_second': entity[20],
                        'rec_type': entity[25]
                    }
                    headers.append(h)
                else:
                    baked_query = db_session.query(DataQar.cycle, DataQar.TS, DataQar.IAS, DataQar.GS, DataQar.ALT_GPS, DataQar.HGT, FDMCalculatedEvent.value, FDMCalculatedEvent.value, FDMCalculatedEvent.param_id).filter(
                        FDMCalculatedEvent.data_qar_id == DataQar.id)
                    h = {
                        'name': entity[1],
                        'front_name': entity[17],
                        'full_name': entity[18],
                        'param_unit': entity[19],
                        'is_second': entity[20],
                        'is_calculated': entity[21],
                        'rec_type': entity[25]
                    }
                    headers.append(h)

            if entity[4]:
                coloring_data.append(entity[1])
                coloring_data.append(entity[5])
                coloring_data.append(entity[8])
                coloring_data.append(entity[9])
                coloring_data.append(entity[10])
                coloring_data.append(entity[11])
                coloring_data.append(entity[16])
                coloring_data.append(entity[20])
                coloring_data.append(entity[22])

        baked_query = baked_query.add_columns(DataQar.cycle, DataQarPhase.description).outerjoin(DataQarPhase, DataQar.PH == DataQarPhase.id)
        if entity[25] == 2 or entity[25] == 4 or entity[25] == 5 or entity[25] == 3:
            results = baked_query.filter(DataQar.id >= results[0][6]-60, DataQar.id <= results[0][7]+60).filter(
                DataQar.session_id == entity[23]).filter(DataQar.cycle == 1).order_by(DataQar.id).all()
        else:
            results = baked_query.filter(DataQar.id >= results[0][6] - 240, DataQar.id <= results[0][7] + 240).filter(
                DataQar.session_id == entity[23]).filter(DataQar.cycle == 1).order_by(DataQar.id).all()

        results2.append(tuple(headers))
        for item in results:
            results2.append(item)

        final_results = []

        final_results.append(tuple(coloring_data))
        final_results.append(results2)

        results3 = db_session.query(FDMMultilimitEvent.limit_warning, FDMMultilimitEvent.limit_caution,
                                    FDMMultilimitEvent.limit_type, DataQar.TS) \
            .filter(and_(FDMEvent.start_id <= FDMMultilimitEvent.data_qar_id,
                                                FDMEvent.stop_id >= FDMMultilimitEvent.data_qar_id)) \
            .filter(FDMEvent.id == event_id) \
            .filter(FDMMultilimitEvent.data_qar_id == DataQar.id) \

        final_results.append(results3)
        return Response(ujson.dumps(final_results), mimetype='application/json')

@restService.route('/event_details/map', methods=['GET'])
@login_required()
def get_event_details_map():
    """
 	Fetch details of details.
 	"""
    if request.method == 'GET':
        event_id = request.args.get('event_id')
        user = request.args.get('user')
        demo_env = os.environ.get('demo_env', 'False')

        logger.info("[%s][Event Details] Event Id: %s",
                    user, event_id)

        event_id = get_int_or_none(event_id)

        results = db_session.query(FDMEvent.id, FDMParam.param_name, FDMParamScale.is_color_scale, FDMEvent.start_id,
                                   FDMEvent.stop_id, ConfFleet.alt_gps_offset, FDMParamScale.limit_type,
                                   FDMEventDetails.min, FDMEventDetails.max,
                                   func.coalesce(ConfAfm.caution, ConfSop.caution).label('caution_limit'),
                                   func.coalesce(ConfAfm.warning, ConfSop.warning).label('warning_limit'),
                                   FDMMultilimitEvent.limit_warning, FDMMultilimitEvent.limit_caution,
                                   func.IF(FDMParamScale.is_max == 0, 1, 2).label('critical_value'), ConfFleet.rec_type) \
            .join(FDMEventLog, FDMEvent.event_type_id == FDMEventLog.event_type_id) \
            .join(FDMParam, FDMEventLog.param_id == FDMParam.id) \
            .join(DataQarSessionIdent, DataQarSessionIdent.session_id == FDMEvent.session_id) \
            .join(DataQarFile, DataQarFile.qar_id == DataQarSessionIdent.qar_id) \
            .join(ConfFleet, ConfFleet.id == DataQarFile.ac_id) \
            .join(FDMEventType, FDMEventType.id == FDMEvent.event_type_id)\
            .outerjoin(FDMParamScale, FDMEventLog.id == FDMParamScale.log_id) \
            .outerjoin(FDMEventDetails, and_(FDMEventDetails.event_id == FDMEvent.id,
                                             FDMEventDetails.param_id == FDMEventLog.param_id)) \
            .outerjoin(ConfAfm, and_(ConfAfm.event_type_id == FDMEvent.event_type_id,
                                     ConfAfm.param_id == FDMEventDetails.param_id,
                                     ConfAfm.ac_type_id == ConfFleet.ac_type,
                                     FDMEventType.limit_source == 'afm')) \
            .outerjoin(ConfSop, and_(ConfSop.event_type_id == FDMEvent.event_type_id,
                                     ConfSop.param_id == FDMEventDetails.param_id,
                                     FDMEventType.limit_source == 'sop')) \
            .outerjoin(FDMMultilimitEvent, FDMEvent.start_id == FDMMultilimitEvent.data_qar_id)\
            .filter(FDMEvent.id == event_id) \
            .all()

        start_id = results[0][3]
        stop_id = results[0][4]
        alt_gps_offset = results[0][5]
        multilimit_warning = results[0][11]
        multilimit_caution = results[0][12]

        param_name = ''
        coloring_data = []

        for entry in results:
            if entry[2]:
                param_name = entry[1]
                coloring_data.append(entry[6])
                coloring_data.append(entry[7])
                coloring_data.append(entry[8])
                coloring_data.append(entry[9])
                coloring_data.append(entry[10])
                coloring_data.append(entry[13])

        prev_data_qar = aliased(DataQar)
        next_data_qar = aliased(DataQar)
        time_alt = 0
        if entry[14] == 4 or entry[14] == 5 or entry[14] == 3 or entry[14] == 2:
            time_alt = 60
        else:
            time_alt = 240

        randLat = random.uniform(0, 1) + 0.75
        randLng = random.uniform(0, 1) + 2.5


        if (param_name == ''):
            param_name = 'IAS'
            results = map(lambda fi: {
                'LAT1': fi.LAT1 - (randLat if (demo_env == 'True') else 0),
                'LNG1': fi.LNG1 - (randLng if (demo_env == 'True') else 0),
                'LAT2': fi.LAT2 - (randLat if (demo_env == 'True') else 0),
                'LNG2': fi.LNG2 - (randLng if (demo_env == 'True') else 0),
                'value': fi.value,
                'time': fi.time,
            }, db_session.query(prev_data_qar.LAT.label('LAT1'), prev_data_qar.LNG.label('LNG1'),
                                next_data_qar.LAT.label('LAT2'), next_data_qar.LNG.label('LNG2'),
                                valueSwitch(param_name, prev_data_qar, alt_gps_offset, multilimit_warning, multilimit_caution).label('value'), prev_data_qar.TS.label('time'))
                          .join(next_data_qar, next_data_qar.id == prev_data_qar.id + 1)
                          .filter(prev_data_qar.id >= start_id-time_alt, prev_data_qar.id <= stop_id+time_alt)
                          .all())
        else:
            results = map(lambda fi: {
                'LAT1': fi.LAT1 - (randLat if (demo_env == 'True') else 0),
                'LNG1': fi.LNG1 - (randLng if (demo_env == 'True') else 0),
                'LAT2': fi.LAT2 - (randLat if (demo_env == 'True') else 0),
                'LNG2': fi.LNG2 - (randLng if (demo_env == 'True') else 0),
                'value': fi.value,
            }, db_session.query(prev_data_qar.LAT.label('LAT1'), prev_data_qar.LNG.label('LNG1'),
                                next_data_qar.LAT.label('LAT2'), next_data_qar.LNG.label('LNG2'),
                                valueSwitch(param_name, prev_data_qar, alt_gps_offset, multilimit_warning, multilimit_caution).label('value'))
                          .join(next_data_qar, next_data_qar.id == prev_data_qar.id + 1)
                          .filter(prev_data_qar.id >= start_id-time_alt, prev_data_qar.id <= stop_id+time_alt)
                          .all())
            results2 = []
            results2.append(tuple(coloring_data))
            results2.append(results)
            results = results2

        return Response(ujson.dumps(results), mimetype='application/json')

@restService.route('/event_details/basic_info', methods=['GET', 'PUT'])
@login_required()
def get_info():
    """
 	Fetch all event list from database.
 	"""
    if request.method == 'GET':
        is_efs = is_efs_connected().response[0]
        user = request.args.get('user')
        event_id = request.args.get('event_id')

        logger.info("[%s][Specific Range]",
                     user)

        sta = aliased(DataQar)
        sto = aliased(DataQar)

        if is_efs == 'true':
            instr = aliased(EFSUser)
            stud = aliased(EFSUser)

            results = map(lambda fi: {
                'event_id': fi.id,
                'event_group': fi.event_group,
                'event_subgroup': fi.event,
                'event_type': fi.description,
                'event_start': fi.start,
                'event_end': fi.end,
                'severity': fi.severity,
                'assigned_to': fi.assigned_to,
                'status': fi.status,
                'importance': fi.importance,
                'student': fi.stud,
                'instructor': fi.instr,
                'ac_type': fi.model,
                'ac_reg': fi.ac_reg,
                'airport_departure': fi.apt_origin,
                'airport_arrival': fi.apt_dest,
                'session_id': fi.session_id
            }, db_session.query(FDMEvent.id, FDMEventSort.description.label('event_group'), FDMEventGroup.event,
                                FDMEventType.description, sta.TS.label('start'), sto.TS.label('end'), FDMEvent.severity,
                                FDMEvent.assigned_to, FDMEvent.status, FDMEvent.importance, ConfAcType.model,
                                ConfFleet.ac_reg, DataQarSessionIdent.apt_origin, DataQarSessionIdent.apt_dest,
                                (stud.first_name + ' ' + stud.last_name).label('stud'),
                                (instr.first_name + ' ' + instr.last_name).label('instr'), FDMEvent.session_id)
                .outerjoin(FDMEventType, FDMEvent.event_type_id == FDMEventType.id)
                .outerjoin(FDMEventGroup, FDMEventType.event_subgroup_id == FDMEventGroup.id)
                .outerjoin(FDMEventSort, FDMEventGroup.event_group_id == FDMEventSort.id)
                .outerjoin(sta, FDMEvent.start_id == sta.id)
                .outerjoin(sto, FDMEvent.stop_id == sto.id)
                .outerjoin(FDMEventParticipant, FDMEvent.id == FDMEventParticipant.event_id)
                .outerjoin(Flight, FDMEventParticipant.flightlog_flt_id == Flight.flight_id)
                .outerjoin(stud, Flight.trainee_id == stud.ID)
                .outerjoin(instr, Flight.instructor_id == instr.ID)
                .outerjoin(DataQarSessionIdent, FDMEvent.session_id == DataQarSessionIdent.session_id)
                .outerjoin(DataQarFile, DataQarSessionIdent.qar_id == DataQarFile.qar_id)
                .outerjoin(ConfFleet, DataQarFile.ac_id == ConfFleet.id)
                .outerjoin(ConfAcType, ConfFleet.ac_type == ConfAcType.id)
                .filter(FDMEvent.id == event_id)
                .all())
        else:
            results = map(lambda fi: {
                'event_id': fi.id,
                'event_group': fi.event_group,
                'event_subgroup': fi.event,
                'event_type': fi.description,
                'event_start': fi.start,
                'event_end': fi.end,
                'severity': fi.severity,
                'assigned_to': fi.assigned_to,
                'status': fi.status,
                'importance': fi.importance,
                'ac_type': fi.model,
                'ac_reg': fi.ac_reg,
                'airport_departure': fi.apt_origin,
                'airport_arrival': fi.apt_dest,
                'session_id': fi.session_id
            }, db_session.query(FDMEvent.id, FDMEventSort.description.label('event_group'), FDMEventGroup.event,
                                FDMEventType.description, sta.TS.label('start'), sto.TS.label('end'), FDMEvent.severity,
                                FDMEvent.assigned_to, FDMEvent.status, FDMEvent.importance, ConfAcType.model,
                                ConfFleet.ac_reg, DataQarSessionIdent.apt_origin, DataQarSessionIdent.apt_dest, FDMEvent.session_id, FDMEventGroup.id)
                          .outerjoin(FDMEventType, FDMEvent.event_type_id == FDMEventType.id)
                          .outerjoin(FDMEventGroup, FDMEventType.event_subgroup_id == FDMEventGroup.id)
                          .outerjoin(FDMEventSort, FDMEventGroup.event_group_id == FDMEventSort.id)
                          .outerjoin(sta, FDMEvent.start_id == sta.id)
                          .outerjoin(sto, FDMEvent.stop_id == sto.id)
                          .outerjoin(DataQarSessionIdent, FDMEvent.session_id == DataQarSessionIdent.session_id)
                          .outerjoin(DataQarFile, DataQarSessionIdent.qar_id == DataQarFile.qar_id)
                          .outerjoin(ConfFleet, DataQarFile.ac_id == ConfFleet.id)
                          .outerjoin(ConfAcType, ConfFleet.ac_type == ConfAcType.id)
                          .filter(FDMEvent.id == event_id)
                          .all())
        editable_results = []
        not_editable_results = []
        header = []

        for item in results[0]:
            o = {
                'property': item,
                'value': results[0][item]
            }
            if item == 'status' or item == 'importance' or item == 'assigned_to':
                editable_results.append(o)
            elif item == 'session_id':
                header.append(o)
            else:
                if is_efs == 'true':
                    if item == 'event_type' or item == 'event_id':
                        not_editable_results.insert(0, o)
                    elif item == 'event_end' or item == 'severity':
                        not_editable_results.insert(1, o)
                    elif item == 'event_group' or item == 'event_subgroup':
                        not_editable_results.insert(2, o)
                    elif item == 'event_start':
                        not_editable_results.insert(4, o)
                    elif item == 'airport_departure' or item == 'instructor':
                        not_editable_results.insert(7, o)
                    elif item == 'student':
                        not_editable_results.insert(6, o)
                    elif item == 'ac_reg':
                        not_editable_results.insert(8, o)
                    else:
                        not_editable_results.append(o)
                else:
                    if item == 'event_type' or item == 'event_id' or item == 'severity' or item == 'event_group':
                        not_editable_results.insert(0, o)
                    elif item == 'event_end':
                        not_editable_results.insert(1, o)
                    elif item == 'event_subgroup':
                        not_editable_results.insert(3, o)
                    elif item == 'event_start':
                        not_editable_results.insert(5, o)
                    elif item == 'airport_departure':
                        not_editable_results.insert(9, o)
                    else:
                        not_editable_results.append(o)

        final_results = []
        final_results.append(editable_results)
        final_results.append(not_editable_results)
        final_results.append(header)


        return Response(ujson.dumps(final_results), mimetype='application/json')

    if request.method == 'PUT':

        if not request.json:
            abort(400)

        assigned_to = None
        status = None
        importance = None
        event_id = None
        e = None
        for item in request.json:
            if(item['property'] == 'assigned_to'):
                assigned_to = item['value']
            if(item['property'] == 'status'):
                status = item['value']
            if(item['property'] == 'importance'):
                importance = item['value']
            if(item['property'] == 'event_id'):
                event_id = item['value']

        user_data = get_user_data(request)

        if event_id:
            e = FDMEvent.query.filter(FDMEvent.id == event_id).first()
            e.assigned_to = assigned_to
            e.status = status
            e.importance = importance
            e.modify_ts = datetime.datetime.now()
            e.modify_user = user_data['id']
        else:
            abort(406)

        try:
            db_session.add(e)
            db_session.commit()
        except:
            abort(400)

        return Response(), 204

@restService.route('/event_details/export_flight', methods=['GET'])
@login_required()
def get_flight_data_to_export():
    if request.method == 'GET':
        event_id = request.args.get('event_id')
        ac_reg_data = request.args.get('ac_reg')

        results = db_session.query(DataQar).filter(DataQar.session_id == db_session.query(FDMEvent.session_id)\
                    .filter(FDMEvent.id == event_id)).all()
        results2 = db_session.query(ConfFleet.alt_gps_offset).filter(ConfFleet.ac_reg == ac_reg_data).all()


        for i in results:
            i.HGT = i.HGT - results2[0][0]
            i.metadata = None
            i._decl_class_registry = None
            i._sa_class_manager = None
            i._sa_instance_state = None
            i.query = None

        return Response(ujson.dumps(results), mimetype='application/json')

@restService.route('/event_details/export_event', methods=['GET'])
@login_required()
def get_event_data_to_export():
    if request.method == 'GET':

        event_id = request.args.get('event_id')
        ac_reg_data = request.args.get('ac_reg')

        logger.info("[Event Details] Event Id: %s",
                     event_id)

        event_id = get_int_or_none(event_id)

        event_start = db_session.query(FDMEvent.start_id).filter(FDMEvent.id == event_id).first()
        event_start = get_int_or_none(event_start[0])
        event_end = db_session.query(FDMEvent.stop_id).filter(FDMEvent.id == event_id).first()
        event_end = get_int_or_none(event_end[0])

        results = db_session.query(DataQar).filter(DataQar.id >= event_start).filter(DataQar.id <= event_end).all()
        results2 = db_session.query(ConfFleet.alt_gps_offset).filter(ConfFleet.ac_reg == ac_reg_data).all()

        for i in results:
            i.HGT = i.HGT - results2[0][0]
            i.metadata = None
            i._decl_class_registry = None
            i._sa_class_manager = None
            i._sa_instance_state = None
            i.query = None

        return Response(ujson.dumps(results), mimetype='application/json')

@restService.route('/event_details/column_name', methods=['GET'])
@login_required()
def get_file_column_name():
    if request.method == 'GET':
        results = db_session.query(ExportParamName.data_qar_name, ExportParamName.export_name, ExportParamName.param_order).all()
        return Response(ujson.dumps(results), mimetype='application/json')

@restService.route('/system_card', methods=['GET'])
@login_required()
def get_data_logging():
    """
 	Fetch all event list from database.
 	"""
    if request.method == 'GET':
        dataType = request.args.get('dataType')

        if dataType == 'last_7_days':

            cau = aliased(FDMEvent)
            war = aliased(FDMEvent)

            results1 = map(lambda fi: {
                'group_type': fi.all_type,
                'group_count': fi.group_count
            }, db_session.query(FDMEvent.id, FDMEventSort.description.label('all_type'),
                                func.count(FDMEvent.event_type_id).label('group_count'))
                           .outerjoin(FDMEventType, FDMEvent.event_type_id == FDMEventType.id) \
                           .outerjoin(FDMEventGroup, FDMEventType.event_subgroup_id == FDMEventGroup.id) \
                           .outerjoin(FDMEventSort, FDMEventGroup.event_group_id == FDMEventSort.id) \
                           .outerjoin(DataQar, FDMEvent.stop_id == DataQar.id)
                           .filter(DataQar.TS <= datetime.datetime.now()) \
                           .filter(DataQar.TS >= (datetime.datetime.now() - datetime.timedelta(days=7))) \
                           .group_by(FDMEventSort.description) \
                           .all() \
                           )

            results2 = map(lambda fi: {
                'events_nr': fi.events_nr,
                'cautions_nr': fi.cautions_nr,
                'warnings_nr': fi.warnings_nr,
                'operations_nr': fi.operations_nr
            },
                           db_session.query(func.count(FDMEvent.session_id.distinct()).label('operations_nr'),
                                            func.count(FDMEvent.id).label('events_nr'),
                                            func.count(cau.id).label('cautions_nr'),
                                            func.count(war.id).label('warnings_nr')) \
                           .outerjoin(DataQarSessionIdent, FDMEvent.session_id == DataQarSessionIdent.session_id) \
                           .outerjoin(DataQarFile, DataQarSessionIdent.qar_id == DataQarFile.qar_id) \
                           .outerjoin(cau, and_(FDMEvent.id == cau.id, cau.severity == 'caution')) \
                           .outerjoin(war, and_(FDMEvent.id == war.id, war.severity == 'warning')) \
                           .outerjoin(DataQar, FDMEvent.stop_id == DataQar.id) \
                           .filter(DataQar.TS <= datetime.datetime.now()) \
                           .filter(DataQar.TS >= (datetime.datetime.now() - datetime.timedelta(days=7))) \
                           )
            results3 = map(lambda fi: {
                'flights_nr': fi.flights_nr
            },
                           db_session.query(func.count(DataQar.flight_id.distinct()).label('flights_nr'))
                           .filter(DataQar.flight_id != 'null')
                           .filter(DataQar.TS <= datetime.datetime.now()) \
                           .filter(DataQar.TS >= (datetime.datetime.now() - datetime.timedelta(days=7))) \
                           )

            results4 = map(lambda fi: {
                'ts': fi.ts
            },
                           db_session.query(FrontDataLogging.ts)
                           .order_by(FrontDataLogging.ts)
                           )

            '''
            results = map(lambda fi: {
                'id': fi.id,
                'processing_id': fi.processing_id,
                'operations_nr': fi.operations_nr,
                'events_nr': fi.events_nr,
                'cautions_nr': fi.cautions_nr,
                'warnings_nr': fi.warnings_nr,
                'ua_nr': fi.ua_nr,
                'cfit_nr': fi.cfit_nr,
                'loc_nr': fi.loc_nr,
                'eo_nr': fi.eo_nr,
                'mac_nr': fi.mac_nr,
                're_nr': fi.re_nr,
                'others_nr': fi.others_nr,
                'ts': fi.ts,
                'flights_nr': fi.flights_nr,
            }, db_session.query(FrontDataLogging.id, FrontDataLogging.processing_id, FrontDataLogging.operations_nr,
                                FrontDataLogging.events_nr, FrontDataLogging.cautions_nr, FrontDataLogging.warnings_nr,
                                FrontDataLogging.ua_nr, FrontDataLogging.cfit_nr, FrontDataLogging.loc_nr,
                                FrontDataLogging.eo_nr, FrontDataLogging.mac_nr, FrontDataLogging.re_nr,
                                FrontDataLogging.others_nr, FrontDataLogging.ts, FrontDataLogging.flights_nr)
                .filter(FrontDataLogging.ts <= datetime.datetime.now()) \
                .filter(FrontDataLogging.ts >= (datetime.datetime.now() - datetime.timedelta(days=7))) \
                .order_by(FrontDataLogging.id.desc()) \
                .all()
                )
            '''

        if dataType == 'last_month':
            cau = aliased(FDMEvent)
            war = aliased(FDMEvent)

            results1 = map(lambda fi: {
                'group_type': fi.all_type,
                'group_count': fi.group_count
            }, db_session.query(FDMEvent.id, FDMEventSort.description.label('all_type'),
                                func.count(FDMEvent.event_type_id).label('group_count'))
                           .outerjoin(FDMEventType, FDMEvent.event_type_id == FDMEventType.id) \
                           .outerjoin(FDMEventGroup, FDMEventType.event_subgroup_id == FDMEventGroup.id) \
                           .outerjoin(FDMEventSort, FDMEventGroup.event_group_id == FDMEventSort.id) \
                           .outerjoin(DataQar, FDMEvent.stop_id == DataQar.id)
                           .filter(DataQar.TS <= datetime.datetime.now()) \
                           .filter(DataQar.TS >= (datetime.datetime.now() - datetime.timedelta(days=30))) \
                           .group_by(FDMEventSort.description) \
                           .all() \
                           )

            results2 = map(lambda fi: {
                'events_nr': fi.events_nr,
                'cautions_nr': fi.cautions_nr,
                'warnings_nr': fi.warnings_nr,
                'operations_nr': fi.operations_nr
            },
                           db_session.query(func.count(FDMEvent.session_id.distinct()).label('operations_nr'),
                                            func.count(FDMEvent.id).label('events_nr'),
                                            func.count(cau.id).label('cautions_nr'),
                                            func.count(war.id).label('warnings_nr')) \
                           .outerjoin(DataQarSessionIdent, FDMEvent.session_id == DataQarSessionIdent.session_id) \
                           .outerjoin(DataQarFile, DataQarSessionIdent.qar_id == DataQarFile.qar_id) \
                           .outerjoin(cau, and_(FDMEvent.id == cau.id, cau.severity == 'caution')) \
                           .outerjoin(war, and_(FDMEvent.id == war.id, war.severity == 'warning')) \
                           .outerjoin(DataQar, FDMEvent.stop_id == DataQar.id) \
                           .filter(DataQar.TS <= datetime.datetime.now()) \
                           .filter(DataQar.TS >= (datetime.datetime.now() - datetime.timedelta(days=30))) \
                           )

            results3 = map(lambda fi: {
                'flights_nr': fi.flights_nr
            },
                           db_session.query(func.count(DataQar.flight_id.distinct()).label('flights_nr'))
                           .filter(DataQar.flight_id != 'null')
                           .filter(DataQar.TS <= datetime.datetime.now()) \
                           .filter(DataQar.TS >= (datetime.datetime.now() - datetime.timedelta(days=30))) \
                           )
            results4 = map(lambda fi: {
                'ts': fi.ts
            },
                           db_session.query(FrontDataLogging.ts)
                           .order_by(FrontDataLogging.ts)
                           )
            '''
            results = map(lambda fi: {
                'id': fi.id,
                'processing_id': fi.processing_id,
                'operations_nr': fi.operations_nr,
                'events_nr': fi.events_nr,
                'cautions_nr': fi.cautions_nr,
                'warnings_nr': fi.warnings_nr,
                'ua_nr': fi.ua_nr,
                'cfit_nr': fi.cfit_nr,
                'loc_nr': fi.loc_nr,
                'eo_nr': fi.eo_nr,
                'mac_nr': fi.mac_nr,
                're_nr': fi.re_nr,
                'others_nr': fi.others_nr,
                'ts': fi.ts,
                'flights_nr': fi.flights_nr,
            }, db_session.query(FrontDataLogging.id, FrontDataLogging.processing_id,
                                func.sum(FrontDataLogging.operations_nr).label('operations_nr'),
                                func.sum(FrontDataLogging.events_nr).label('events_nr'),
                                func.sum(FrontDataLogging.cautions_nr).label('cautions_nr'),
                                func.sum(FrontDataLogging.warnings_nr).label('warnings_nr'),
                                func.sum(FrontDataLogging.ua_nr).label('ua_nr'),
                                func.sum(FrontDataLogging.cfit_nr).label('cfit_nr'),
                                func.sum(FrontDataLogging.loc_nr).label('loc_nr'),
                                func.sum(FrontDataLogging.eo_nr).label('eo_nr'),
                                func.sum(FrontDataLogging.mac_nr).label('mac_nr'),
                                func.sum(FrontDataLogging.re_nr).label('re_nr'),
                                func.sum(FrontDataLogging.others_nr).label('others_nr'), FrontDataLogging.ts,
                                func.sum(FrontDataLogging.flights_nr).label('flights_nr'))
                          .filter(FrontDataLogging.ts <= datetime.datetime.now()) \
                          .filter(FrontDataLogging.ts >= (datetime.datetime.now() - datetime.timedelta(days=30)) )\
                          .order_by(FrontDataLogging.id.desc()) \
                          .all()
                          )
                          
                          '''
        if dataType == 'all':
            cau = aliased(FDMEvent)
            war = aliased(FDMEvent)

            results1 = map(lambda fi: {
                'group_type': fi.all_type,
                'group_count': fi.group_count
            }, db_session.query(FDMEvent.id, FDMEventSort.description.label('all_type'), func.count(FDMEvent.event_type_id).label('group_count'))
                    .outerjoin(FDMEventType, FDMEvent.event_type_id == FDMEventType.id) \
                    .outerjoin(FDMEventGroup, FDMEventType.event_subgroup_id == FDMEventGroup.id) \
                    .outerjoin(FDMEventSort, FDMEventGroup.event_group_id == FDMEventSort.id) \
                    .group_by(FDMEventSort.description) \
                    .all() \
                    )

            results2 = map(lambda fi: {
                'events_nr': fi.events_nr,
                'cautions_nr': fi.cautions_nr,
                'warnings_nr': fi.warnings_nr,
                'operations_nr': fi.operations_nr
            },
                db_session.query(func.count(FDMEvent.session_id.distinct()).label('operations_nr'), func.count(FDMEvent.id).label('events_nr'),
                       func.count(cau.id).label('cautions_nr'), func.count(war.id).label('warnings_nr')) \
                    .outerjoin(DataQarSessionIdent, FDMEvent.session_id == DataQarSessionIdent.session_id) \
                .outerjoin(DataQarFile, DataQarSessionIdent.qar_id == DataQarFile.qar_id) \
                .outerjoin(cau, and_(FDMEvent.id == cau.id, cau.severity == 'caution')) \
                .outerjoin(war, and_(FDMEvent.id == war.id, war.severity == 'warning')) \
            )
            print '######'
            results3 = map(lambda fi: {
                'flights_nr': fi.flights_nr
            },
                           db_session.query(func.count(DataQar.flight_id.distinct()).label('flights_nr'))
                           .filter(DataQar.flight_id != 'null')

                           )
            results4 = map(lambda fi: {
                'ts': fi.ts
            },
                           db_session.query(FrontDataLogging.ts)
                        .order_by(FrontDataLogging.ts)
                        )

        result = results1+results2+results3+results4
        return Response(ujson.dumps(result), mimetype='application/json')

@restService.route('/system_card_user_info', methods=['GET'])
@login_required()
def get_data_logging_user():
    """
 	Fetch all event list from database.
 	"""
    if request.method == 'GET':
        dataType = request.args.get('dataType')

        if dataType == 'all':
            results1 = map(lambda fi: {
                'all_events': fi.all_events
            }, db_session.query(func.count(FDMEvent.id).label('all_events'))
                .all()
                )

            results2 = map(lambda fi: {
                'new_events': fi.new_events,
            }, db_session.query(func.count(FDMEvent.id).label('new_events'))
                .filter(FDMEvent.status == None)
                .all()
                )

            results3 = map(lambda fi: {
                'in_progress': fi.in_progress,
            }, db_session.query(func.count(FDMEvent.id).label('in_progress'))
                           .filter(FDMEvent.status == "in progress")
                           .all()
                           )

            results4 = map(lambda fi: {
                'analysed': fi.analysed,
            }, db_session.query(func.count(FDMEvent.id).label('analysed'))
                           .filter(FDMEvent.status == "analysed")
                           .all()
                           )

        if dataType == 'last_7_days':
            results1 = map(lambda fi: {
                'all_events': fi.all_events
            }, db_session.query(func.count(FDMEvent.id).label('all_events'))
                .outerjoin(DataQarSessionIdent, FDMEvent.session_id == DataQarSessionIdent.session_id) \
                .filter(DataQarSessionIdent.block_off <= datetime.datetime.now()) \
                .filter(DataQarSessionIdent.block_off >= (datetime.datetime.now() - datetime.timedelta(days=7))) \
                .all()
                )

            results2 = map(lambda fi: {
                'new_events': fi.new_events,
            }, db_session.query(func.count(FDMEvent.id).label('new_events'))
                .filter(FDMEvent.status == None)
                .filter(DataQarSessionIdent.block_off <= datetime.datetime.now()) \
                .filter(DataQarSessionIdent.block_off >= (datetime.datetime.now() - datetime.timedelta(days=7))) \
                .all()
                )

            results3 = map(lambda fi: {
                'in_progress': fi.in_progress,
            }, db_session.query(func.count(FDMEvent.id).label('in_progress'))
                           .filter(FDMEvent.status == "in progress")
                           .filter(DataQarSessionIdent.block_off <= datetime.datetime.now()) \
                           .filter(DataQarSessionIdent.block_off >= (datetime.datetime.now() - datetime.timedelta(days=7))) \
                           .all()
                           )

            results4 = map(lambda fi: {
                'analysed': fi.analysed,
            }, db_session.query(func.count(FDMEvent.id).label('analysed'))
                           .filter(FDMEvent.status == "analysed")
                           .filter(DataQarSessionIdent.block_off <= datetime.datetime.now()) \
                           .filter(DataQarSessionIdent.block_off >= (datetime.datetime.now() - datetime.timedelta(days=7))) \
                           .all()
                           )

        if dataType == 'last_month':
            results1 = map(lambda fi: {
                'all_events': fi.all_events
            }, db_session.query(func.count(FDMEvent.id).label('all_events'))
                .outerjoin(DataQarSessionIdent, FDMEvent.session_id == DataQarSessionIdent.session_id) \
                .filter(DataQarSessionIdent.block_off <= datetime.datetime.now()) \
                .filter(DataQarSessionIdent.block_off >= (datetime.datetime.now() - datetime.timedelta(days=30))) \
                .all()
                )

            results2 = map(lambda fi: {
                'new_events': fi.new_events,
            }, db_session.query(func.count(FDMEvent.id).label('new_events'))
                .filter(FDMEvent.status == None)
                .filter(DataQarSessionIdent.block_off <= datetime.datetime.now()) \
                .filter(DataQarSessionIdent.block_off >= (datetime.datetime.now() - datetime.timedelta(days=30))) \
                .all()
                )

            results3 = map(lambda fi: {
                'in_progress': fi.in_progress,
            }, db_session.query(func.count(FDMEvent.id).label('in_progress'))
                           .filter(FDMEvent.status == "in progress")
                           .filter(DataQarSessionIdent.block_off <= datetime.datetime.now()) \
                           .filter(DataQarSessionIdent.block_off >= (datetime.datetime.now() - datetime.timedelta(days=30))) \
                           .all()
                           )

            results4 = map(lambda fi: {
                'analysed': fi.analysed,
            }, db_session.query(func.count(FDMEvent.id).label('analysed'))
                           .filter(FDMEvent.status == "analysed")
                           .filter(DataQarSessionIdent.block_off <= datetime.datetime.now()) \
                           .filter(DataQarSessionIdent.block_off >= (datetime.datetime.now() - datetime.timedelta(days=30))) \
                           .all()
                           )


        results = results1 + results2 + results3 + results4

        return Response(ujson.dumps(results), mimetype='application/json')


@restService.route('/efs_connect', methods=['GET'])
@login_required()
def is_efs_connected():
    if request.method == 'GET':
        is_access = map(lambda fi: {
            'value': fi.value,
        }, db_session.query(ConfFDMApi.value)
                       )
        if is_access[0]['value'] == 'True':
            results = True
        else:
            results = False

        return Response(ujson.dumps(results), content_type='application/json')


@restService.route('/event_stats/data', methods=['GET'])
@login_required()
def get_events_stats_data():
    temparray = request.args.get('events_id')
    temparray1 = request.args.get('programs_id')
    events_id = ProcessData(temparray) #Transform data
    programs_id = ProcessData(temparray1)  # Transform data
    chart_type = request.args.get('chart_type')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    student = request.args.get('student')
    instructor = request.args.get('instructor')
    ac = request.args.get('ac')
    apt_dep = request.args.get('apt_dep')
    apt_arr = request.args.get('apt_arr')
    severity = request.args.get('severity')
    time_aggregation = request.args.get('time_aggregation')
    event_with_program = request.args.get('event_with_program')
    if request.method == 'GET':

        is_efs = is_efs_connected().response[0]
        sta = aliased(DataQar)
        sto = aliased(DataQar)
        stud = aliased(EFSUser)
        instr = aliased(EFSUser)
        if is_efs == 'true':
            baked_query = db_session.query(func.count(FDMEvent.id).label('value'),
                                           ConfAcType.model, ConfFleet.ac_reg, Flight.trainee_id, Flight.training_prog_id, Flight.instructor_id, Program.name,
                                           func.date_format(sta.TS, '%m/%Y').label('month'), func.date_format(sta.TS, '%Y').label('year'),
                                           func.date_format(sta.TS, '%d/%m/%Y').label('day'), sta.TS,
                                           func.IF(Flight.instructor_id, (instr.first_name + ' ' + instr.last_name), 'None').label('instr'),
                                           func.IF(Flight.trainee_id, (stud.first_name + ' ' + stud.last_name),'None').label('stud')) \
                          .join(FDMEventType, FDMEvent.event_type_id == FDMEventType.id)\
                          .join(FDMEventGroup, FDMEventType.event_subgroup_id == FDMEventGroup.id)\
                          .join(FDMEventSort, FDMEventGroup.event_group_id == FDMEventSort.id)\
                          .join(sta, FDMEvent.start_id == sta.id)\
                          .join(sto, FDMEvent.stop_id == sto.id)\
                          .join(DataQarSessionIdent, FDMEvent.session_id == DataQarSessionIdent.session_id)\
                          .join(DataQarFile, DataQarSessionIdent.qar_id == DataQarFile.qar_id)\
                          .join(ConfFleet, DataQarFile.ac_id == ConfFleet.id)\
                          .join(ConfAcType, ConfFleet.ac_type == ConfAcType.id) \

        else:
            baked_query = db_session.query(func.count(FDMEvent.id).label('value'),
                                           ConfAcType.model, ConfFleet.ac_reg,
                                           func.date_format(sta.TS, '%m/%Y').label('month'),
                                           func.date_format(sta.TS, '%Y').label('year'),
                                           func.date_format(sta.TS, '%d/%m/%Y').label('day'), sta.TS ) \
                .join(FDMEventType, FDMEvent.event_type_id == FDMEventType.id) \
                .join(FDMEventGroup, FDMEventType.event_subgroup_id == FDMEventGroup.id) \
                .join(FDMEventSort, FDMEventGroup.event_group_id == FDMEventSort.id) \
                .join(sta, FDMEvent.start_id == sta.id) \
                .join(sto, FDMEvent.stop_id == sto.id) \
                .join(DataQarSessionIdent, FDMEvent.session_id == DataQarSessionIdent.session_id) \
                .join(DataQarFile, DataQarSessionIdent.qar_id == DataQarFile.qar_id) \
                .join(ConfFleet, DataQarFile.ac_id == ConfFleet.id) \
                .join(ConfAcType, ConfFleet.ac_type == ConfAcType.id) \

        if is_efs == 'true':
            if event_with_program == 0 or event_with_program == "0":
                baked_query = baked_query.join(FDMEventParticipant, FDMEvent.id == FDMEventParticipant.event_id) \
                .outerjoin(Flight, FDMEventParticipant.flightlog_flt_id == Flight.flight_id) \
                .outerjoin(Program, Flight.training_prog_id == Program.id) \
                .outerjoin(stud, Flight.trainee_id == stud.ID) \
                .outerjoin(instr, Flight.instructor_id == instr.ID) \

            else:
                baked_query = baked_query.outerjoin(FDMEventParticipant, FDMEvent.id == FDMEventParticipant.event_id) \
                .outerjoin(Flight, FDMEventParticipant.flightlog_flt_id == Flight.flight_id) \
                .outerjoin(Program, Flight.training_prog_id == Program.id) \
                .outerjoin(stud, Flight.trainee_id == stud.ID) \
                .outerjoin(instr, Flight.instructor_id == instr.ID) \

        stud1 = aliased(EFSUser)
        instr1 = aliased(EFSUser)
        baked_query_2 = db_session.query(func.Count(DataQarFlightIdent.id).label('flight_time'), func.date_format(DataQarSessionIdent.block_off, '%m/%Y').label('month'),
                    func.date_format(DataQarSessionIdent.block_off, '%d/%m/%Y').label('day'), func.date_format(DataQarSessionIdent.block_off, '%Y').label('year'),
                                          ConfAcType.model, ConfFleet.ac_reg ) \
                                                  .outerjoin(FDMFlightParticipant, DataQarFlightIdent.flight_id == FDMFlightParticipant.flight_id) \
                                                  .outerjoin(DataQarSessionIdent, DataQarFlightIdent.session_id == DataQarSessionIdent.session_id) \
                                                  .outerjoin(DataQarFile, DataQarSessionIdent.qar_id == DataQarFile.qar_id) \
                                                  .outerjoin(ConfFleet, DataQarFile.ac_id == ConfFleet.id) \
                                                  .outerjoin(ConfAcType, ConfFleet.ac_type == ConfAcType.id) \

        if is_efs == 'true':
            baked_query_2 = baked_query_2.add_columns(func.IF(Flight.instructor_id, (instr1.first_name + ' ' + instr1.last_name),'None').label('instr'),
                                         func.IF(Flight.trainee_id, (stud1.first_name + ' ' + stud1.last_name),'None').label('stud'), Program.name) \
                                    .outerjoin(Flight, FDMFlightParticipant.flightlog_flt_id == Flight.flight_id) \
                                    .outerjoin(stud1, Flight.trainee_id == stud1.ID).outerjoin(instr1, Flight.instructor_id == instr1.ID) \
                                    .outerjoin(Program, Flight.training_prog_id == Program.id) \

        if is_efs == 'false':
            if chart_type == 'events_per_program' or chart_type == 'events_per_instructor' or chart_type == 'events_per_student':
                abort(400)

        if date_from != 'null':
            baked_query = baked_query.filter(DataQarSessionIdent.block_off > date_from)
            baked_query_2 = baked_query_2.filter(DataQarSessionIdent.block_off > date_from)

        if date_to != 'null':
            baked_query = baked_query.filter(DataQarSessionIdent.block_off < date_to)
            baked_query_2 = baked_query_2.filter(DataQarSessionIdent.block_off < date_to)

        if student != 'null':
            baked_query = baked_query.filter(Flight.trainee_id == student)
            baked_query_2 = baked_query_2.filter(Flight.trainee_id == student)

        if instructor != 'null':
            baked_query = baked_query.filter(Flight.instructor_id == instructor)
            baked_query_2 = baked_query_2.filter(Flight.instructor_id == instructor)

        if ac != 'null':
            baked_query = baked_query.filter(ConfFleet.ac_type == ac)
            baked_query_2 = baked_query_2.filter(ConfFleet.ac_type == ac)

        if apt_dep != 'null':
            baked_query = baked_query.filter(DataQarSessionIdent.apt_origin == apt_dep)
            baked_query_2 = baked_query_2.filter(DataQarSessionIdent.apt_origin == apt_dep)

        if apt_arr != 'null':
            baked_query = baked_query.filter(DataQarSessionIdent.apt_dest == apt_arr)
            baked_query_2 = baked_query_2.filter(DataQarSessionIdent.apt_dest == apt_arr)

        if severity != 'null':
            baked_query = baked_query.filter(FDMEvent.severity == severity)

        if len(events_id) > 0 and events_id[0] != -1:
            baked_query = baked_query.filter(FDMEvent.event_type_id.in_(events_id))
        if events_id == []:
            baked_query = baked_query.filter(FDMEvent.event_type_id.in_([]))

        if is_efs == 'true':
            if len(programs_id) > 0 and programs_id[0] != -1:
                baked_query = baked_query.filter(or_(Flight.training_task_id.in_(programs_id), FDMEventParticipant.flightlog_flt_id == None))
            if programs_id == []:
                baked_query = baked_query.filter(or_(Flight.training_task_id.in_([]), FDMEventParticipant.flightlog_flt_id == None))

        if chart_type == 'trend_in_time':
            if time_aggregation == 'day':
                baked_query = baked_query.group_by(func.date_format(sta.TS, '%d/%m/%Y')).order_by(sta.TS)
                baked_query_2 = baked_query_2.group_by(func.date_format(DataQarSessionIdent.block_off, '%d/%m/%Y')).order_by(DataQarSessionIdent.block_off)
                results = map(lambda fi: {
                    'value': fi.value,
                    'key': fi.day,
                    }, baked_query.all()
                )
                results2 = map(lambda fi: {
                    'value2': fi.flight_time,
                    'key': fi.day,
                }, baked_query_2.all()
                               )

            elif time_aggregation == 'month':
                baked_query = baked_query.group_by(func.date_format(sta.TS, '%m/%Y')).order_by(sta.TS)
                baked_query_2 = baked_query_2.group_by(func.date_format(DataQarSessionIdent.block_off, '%m/%Y')).order_by(DataQarSessionIdent.block_off)
                results = map(lambda fi: {
                    'value': fi.value,
                    'key': fi.month,
                    }, baked_query.all()
                )
                results2 = map(lambda fi: {
                    'value2': fi.flight_time,
                    'key': fi.month,
                }, baked_query_2.all()
                               )

            elif time_aggregation == 'year':
                baked_query = baked_query.group_by(func.date_format(sta.TS, '%Y')).order_by(sta.TS)
                baked_query_2 = baked_query_2.group_by(func.date_format(DataQarSessionIdent.block_off, '%Y')).order_by(DataQarSessionIdent.block_off)
                results = map(lambda fi: {
                    'value': fi.value,
                    'key': fi.year,
                    }, baked_query.all()
                )
                results2 = map(lambda fi: {
                    'value2': fi.flight_time,
                    'key': fi.year,
                }, baked_query_2.all()
                               )
        elif chart_type == 'events_per_students':
            baked_query = baked_query.filter(Flight.trainee_id != None).group_by(Flight.trainee_id).order_by(stud.last_name)
            baked_query_2 = baked_query_2.filter(Flight.trainee_id != None).group_by(Flight.trainee_id).order_by(stud1.last_name)
            results = map(lambda fi: {
                'value': fi.value,
                'key': fi.stud
                }, baked_query.all()
            )
            results2 = map(lambda fi: {
                'value2': fi.flight_time,
                'key': fi.stud,
            }, baked_query_2.all()
                           )
        elif chart_type == 'events_per_instructors':
            baked_query = baked_query.filter(Flight.instructor_id != None).group_by(Flight.instructor_id).order_by(instr.last_name)
            baked_query_2 = baked_query_2.filter(Flight.instructor_id != None).group_by(Flight.instructor_id).order_by(instr1.last_name)
            results = map(lambda fi: {
                'value': fi.value,
                'key': fi.instr
            }, baked_query.all()
                          )
            results2 = map(lambda fi: {
                'value2': fi.flight_time,
                'key': fi.instr,
            }, baked_query_2.all()
                           )
        elif chart_type == 'events_per_ac_type':
            baked_query = baked_query.group_by(ConfFleet.ac_type).order_by(ConfAcType.model)
            baked_query_2 = baked_query_2.group_by(ConfFleet.ac_type).order_by(ConfAcType.model)
            results = map(lambda fi: {
                'value': fi.value,
                'key': fi.model
            }, baked_query.all()
                          )
            results2 = map(lambda fi: {
                'value2': fi.flight_time,
                'key': fi.model,
            }, baked_query_2.all()
                           )
        elif chart_type == 'events_per_ac_reg':
            baked_query = baked_query.group_by(ConfFleet.ac_reg).order_by(ConfFleet.ac_reg)
            baked_query_2 = baked_query_2.group_by(ConfFleet.ac_type).order_by(ConfAcType.model)
            results = map(lambda fi: {
                'value': fi.value,
                'key': fi.ac_reg
            }, baked_query.all()
                          )
            results2 = map(lambda fi: {
                'value2': fi.flight_time,
                'key': fi.ac_reg,
            }, baked_query_2.all()
                           )
        elif chart_type == 'events_per_program':
            baked_query = baked_query.group_by(Flight.training_prog_id)
            baked_query_2 = baked_query_2.group_by(Flight.training_prog_id)
            results = map(lambda fi: {
                'value': fi.value,
                'key': fi.name
            }, baked_query.all()
                          )

            results2 = map(lambda fi: {
                'value2': fi.flight_time,
                'key': fi.name,
            }, baked_query_2.all()
                           )

        results = results + results2
        return Response(ujson.dumps(results), content_type='application/json')


@restService.route('/students', methods=['GET'])
@login_required()
def get_students():

        is_efs = is_efs_connected().response[0]
        if is_efs == 'true':
            results = map(lambda fi: {
                'value': fi.ID,
                'label': fi.user
            }, db_session.query((EFSUser.first_name + ' ' + EFSUser.last_name).label('user'), EFSUser.ID)
                          .filter(EFSUser.group_id == 18).all())
        else:
            results = None

        return Response(ujson.dumps(results, ensure_ascii=False), content_type='application/json')


@restService.route('/instructors', methods=['GET'])
@login_required()
def get_instructors():

        is_efs = is_efs_connected().response[0]
        if is_efs == 'true':
            results = map(lambda fi: {
                'value': fi.ID,
                'label': fi.user.encode('UTF8')
            }, db_session.query((EFSUser.first_name + ' ' + EFSUser.last_name).label('user'), EFSUser.ID)
                          .filter(or_(EFSUser.group_id == 19, EFSUser.group_id == 20)).all())
        else:
            results = None
        return Response(ujson.dumps(results, ensure_ascii=False), content_type='application/json')


@restService.route('/airports', methods=['GET'])
@login_required()
def get_airports():

        results = map(lambda fi: {
            'value': fi.icao,
            'label': fi.icao
        }, db_session.query(CoreAirport.icao).all())

        return Response(ujson.dumps(results), content_type='application/json')


@restService.route('/aircrafts', methods=['GET'])
@login_required()
def get_aircrafts():

        results = map(lambda fi: {
            'value': fi.id,
            'label': fi.model
        }, db_session.query(ConfAcType.id, ConfAcType.model).all())

        return Response(ujson.dumps(results), content_type='application/json')
