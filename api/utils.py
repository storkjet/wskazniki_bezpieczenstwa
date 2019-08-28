#-*- coding: utf-8 -*-
from datetime import datetime
import re

date_format = '%Y-%m-%d'

def get_formated_date(date_str):
	if date_str is not None and date_str != '':
		date_str = date_str.replace('"', '')
		
		return datetime.strptime(date_str[0:10], date_format)

	return None

def get_int_or_none(int_str):
	if int_str is not None and int_str != '':
		return int(int_str)

	return 0

def get_float(float_str):
	return float(float_str)

def get_method(str):
	if str == 'step' or str == 'smooth':
		return str
	raise ValueError('Wrong method')

def get_delta(str):
	temp = float(str)
	if temp > 1:
		return 1
	elif temp < 0:
		return 0
	else:
		return temp

def get_update(str):
	if str == 'QUARTER' or str == 'MONTH':
		return str
	raise ValueError('Wrong update frequency')

def get_negatives(str):
	temp = int(str)
	if temp > 1 or temp < 0:
		return 1
	return temp

def get_email(str):
	if str != None:
		if re.match(r"[^@]+@[^@]+\.[^@]+", str):
			return str
	return None

def get_smooth(str):
	temp = int(str)
	if temp < 1 or temp > 12:
		return 1
	else:
		return temp

def get_rounding(str):
	if str == 'both' or str == 'up' or str == 'down':
		return str
	raise ValueError('Wrong rouding method')