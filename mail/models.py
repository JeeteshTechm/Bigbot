from django.db import models
from core.models import Preference
from django.template.loader import get_template
from django.template import Context, Template
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail,To
from django.conf import settings