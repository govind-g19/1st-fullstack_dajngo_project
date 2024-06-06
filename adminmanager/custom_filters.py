from django import template

register = template.Library()


@register.filter
def dictlookup(dictionary, key):
    return dictionary.get(key)
