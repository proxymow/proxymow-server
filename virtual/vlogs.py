import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_MAX_BYTES = 1000000
LOG_BACKUP_COUNT = 10


def init(work_folder_path=Path('/home/pi')):

    log_file_name = (work_folder_path / 'logs' / 'virtual.log').resolve().__str__()

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
