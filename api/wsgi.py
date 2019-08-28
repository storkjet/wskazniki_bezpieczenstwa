from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from os import environ

import logging

from api import app

logger = logging.getLogger()

fileHandler = logging.FileHandler('wskazniki_bezpieczenstwa.log')
consoleHandler = logging.StreamHandler()

logger.addHandler(fileHandler)
logger.addHandler(consoleHandler)

http_server = HTTPServer(WSGIContainer(app))

http_server.listen(environ['API_PORT'])

IOLoop.instance().start()
