from django import template

register = template.Library()

@register.filter
def startswith(text, starts):
     return text.startswith(starts)

