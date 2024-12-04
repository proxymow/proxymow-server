import logging
from logging.handlers import RotatingFileHandler

log_file_name = '/home/pi/logs/virtual.log'
LOG_MAX_BYTES = 1000000
LOG_BACKUP_COUNT = 10

# control functions


def init():

    # create formatter
    log_formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S")

    # main log
    vlogger = logging.getLogger('virtual')
    # create handler
    log_handler = RotatingFileHandler(
        log_file_name, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT)
    # add formatter to handler
    log_handler.setFormatter(log_formatter)
    vlogger.addHandler(log_handler)
    vlogger.setLevel(logging.DEBUG)


def trace_virtual(msg):
    vlogger = logging.getLogger('virtual')
    try:
        vlogger.info(msg)
    except:
        pass
