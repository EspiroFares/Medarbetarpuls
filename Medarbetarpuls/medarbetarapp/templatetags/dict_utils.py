# In templatetags you can put a Python module (like my_tags.py or dict_utils.py) that defines:
# •	template filters (like {{ mydict|get_item:"key" }})
# •	template tags (like {% my_custom_tag %})
# You use @register.filter and @register.simple_tag decorators to define them.

from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, key)  # fallback to key if not found
