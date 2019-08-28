#-*- coding: utf-8 -*-

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from os import environ

connect_args = {'init_command':"SET NAMES 'utf8'"}

engine = create_engine('mysql://' + environ['DB_USER'] + ':' + environ['DB_PASS'] + '@' + environ['DB_HOST'] + '/' +
                       environ['DB_NAME'] + '', connect_args=connect_args, pool_recycle=3600, echo=True)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

Base = declarative_base()
Base.query = db_session.query_property()

def init_db():
    import models
    Base.metadata.create_all(bind=engine)

def table_exists(name):
    ret = engine.dialect.has_table(engine, name)
    return ret