import fluent.handler
import logging
from colorit import init_colorit, color, background
from enum import Enum
from typing import List, Dict, Optional
from django.conf import settings

init_colorit()

class Color(Enum):
    BLUE = color.blue
    RED = color.red
    PURPLE = color.purple
    GREEN = color.green
    ORANGE = color.orange

def log(tag: str, message: str, color: Optional[Color]=None, bg_color: Optional[Color]=None, fluentd_logger: Optional[logging.Logger]=None):
    if bg_color:
        log_message = background(f"{tag}: {message}", bg_color.value)
    else:
        log_message = color.value(f"{tag}: {message}")
    print(log_message)
    if fluentd_logger:
        fluentd_logger.info(message, extra={'tag': tag, 'color': color.name if color else None, 'bg_color': bg_color.name if bg_color else None})

def debug(tag: str, message: str, color: Optional[Color]=Color.BLUE, fluentd_logger: Optional[logging.Logger]=None):
    if settings.DEBUG:
        log(tag, message, color, fluentd_logger=fluentd_logger)

def error(tag: str, message: str, color: Optional[Color]=Color.RED, fluentd_logger: Optional[logging.Logger]=None):
    log(tag, message, color, fluentd_logger=fluentd_logger)

def info(tag: str, message: str, color: Optional[Color]=Color.PURPLE, fluentd_logger: Optional[logging.Logger]=None):
    log(tag, message, color, fluentd_logger=fluentd_logger)

def message(tag: str, message: str, green: bool=False, fluentd_logger: Optional[logging.Logger]=None):
    bg_color = Color.GREEN if green else Color.RED
    log(tag, message, bg_color=bg_color, fluentd_logger=fluentd_logger)

def warning(tag: str, message: str, color: Optional[Color]=Color.ORANGE, fluentd_logger: Optional[logging.Logger]=None):
    log(tag, message, color, fluentd_logger=fluentd_logger)

def fluentd_config(host: str, port: int, tag: str) -> Dict[str, str]:
    return {
        'host': host,
        'port': port,
        'tag': tag
    }

def setup_fluentd_logging(config: Dict[str, str]) -> logging.Logger:
    handler = fluent.handler.FluentHandler(config['tag'], host=config['host'], port=config['port'])
    handler.setFormatter(fluent.handler.FluentRecordFormatter())
    logger = logging.getLogger('fluent')
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger
