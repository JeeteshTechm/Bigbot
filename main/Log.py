from colorit import init_colorit, color, background
from django.conf import settings

init_colorit()

def log(tag, *args, color_func=color, bg_color=None):
    args = ", ".join([str(item) for item in args])
    if bg_color:
        print(background(f"{tag}: {args}", bg_color))
    else:
        print(color_func(f"{tag}: {args}", color_func))

def debug(tag, *args):
    if settings.DEBUG:
        log(tag, *args, color_func=Colors.blue)

def error(tag, *args):
    log(tag, *args, color_func=Colors.red)

def info(tag, *args):
    log(tag, *args, color_func=Colors.purple)

def message(tag, *args, green=False):
    log(tag, *args, bg_color=Colors.green if green else Colors.red)

def warning(tag, *args):
    log(tag, *args, color_func=Colors.orange)
