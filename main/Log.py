import fluent.handler
import logging
from colorit import init_colorit, color, Colors, background
from enum import Enum
from typing import List, Dict, Optional
from django.conf import settings

init_colorit()

class Color(Enum):
    BLUE = Colors.blue
    RED = Colors.red
    PURPLE = Colors.purple
    GREEN = Colors.green
    ORANGE = Colors.orange

def log(tag: str, message: str, foreground_color: Optional[Color]=None, bg_color: Optional[Color]=None, fluentd_logger: Optional[logging.Logger]=None):
    if bg_color:
        log_message = background(f"{tag}: {message}", bg_color.value)
    else:
        try:
            log_message = color(f"{tag}: {message}", foreground_color.value)
        except AttributeError as ex:
            pass
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
