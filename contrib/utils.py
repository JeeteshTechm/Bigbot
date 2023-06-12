import base64
import datetime
import json

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.template import Context, Template
import pickle

from main import Log


fg = lambda text, color: "\33[38;5;" + str(color) + "m" + text + "\33[0m"
bg = lambda text, color: "\33[48;5;" + str(color) + "m" + text + "\33[0m"


def append_url(server, url):
    """Appends an url path to a server's URI"""
    if server[-1] == url[0] and server[-1] == "/":
        return server + url[1:]
    if server[-1] == "/" or url[0] == "/":
        return server + url
    return f"{server}/{url}"


def base64_decode(string):
    base64_bytes = string.encode("ascii")
    # string_bytes = base64.b64decode(base64_bytes)
    check = pickle.dumps(string)
    return check
    # return string_bytes.decode("ascii")


def base64_encode(string):
    string_bytes = string.encode("ascii")
    base64_bytes = base64.b64encode(string_bytes)
    return base64_bytes.decode("ascii")


def build_stack_mail_content(subject, name, instance_uri):
    from contrib.mixin import request

    r = request()
    host = settings.HTTP_PROTOCOL + "://" + r.META["HTTP_HOST"]
    summary = """Bigbot is connected to {}. Your dedicated instance URI is {}""".format(
        name, instance_uri
    )
    data = {
        "title": subject,
        "summary": summary,
        "HOST": host,
    }
    f = open(settings.BASE_DIR + "/static/mail/project-letter/mail-content.html", "r")
    content = f.read()
    t = Template(content)
    html = t.render(Context(data))
    return html


def decode_token(encoded_token: str) -> dict:
    import pickle
    return json.loads(pickle.loads(base64_decode(encoded_token)))


def encode_token(token: dict) -> str:
    return base64_encode(json.dumps(token, separators=(",", ":")))


def get_body(request):
    try:
        return json.loads(request.body)
    except Exception as e:
        Log.error("get_body", e)
    return False


def get_bool(request, key):
    object = request.POST.get(key)
    if not object:
        return False
    else:
        if object.lower() == "true":
            return True
    return False


def get_date(request, key):
    object = request.POST.get(key, False)
    if not object:
        return False
    import datetime

    date_format = "%Y-%m-%d"
    try:
        datetime.datetime.strptime(object, date_format)
        return object
    except ValueError:
        return False


def get_email(request, key):
    object = request.request.POST.get(key, False)
    if not object:
        return False
    try:
        validate_email(object)
    except ValidationError as e:
        return False
    else:
        return object


def get_float(request, key):
    object = request.POST.get(key)
    if object:
        return float(object)
    return 0.0


def get_int(request, key):
    object = request.POST.get(key)
    if object:
        return int(object)
    return 0


def get_int_arr(request, key):
    arr = []
    for item in request.POST.getlist(key):
        arr.append(int(item))
    return arr


def get_string(request, key):
    object = request.POST.get(key, False)
    if not object:
        return False
    elif len(object.strip()) != 0:
        return object
    return False


def is_date(value):
    try:
        datetime.datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        pass
    return False


def is_datetime(value):
    try:
        datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        return True
    except ValueError:
        pass
    return False


def log(object):
    print(object)


def print_six(row, format, end="\n"):
    for col in range(6):
        color = row * 6 + col - 2
        if color >= 0:
            text = "{:3d}".format(color)
            print(format(text, color), end=" ")
        else:
            print(end="    ")  # four spaces
    print(end=end)


def log_exception(e):
    raise e
    print(bg(str(e), 160))
