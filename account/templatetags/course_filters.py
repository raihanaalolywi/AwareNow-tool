# account/templatetags/course_filters.py
from django import template

register = template.Library()

@register.filter
def youtube_embed(url):
    """Convert YouTube watch URL to embed URL"""
    if 'youtube.com/watch?v=' in url:
        return url.replace('youtube.com/watch?v=', 'youtube.com/embed/')
    elif 'youtu.be/' in url:
        video_id = url.split('youtu.be/')[-1].split('?')[0]
        return f'https://youtube.com/embed/{video_id}'
    return url

@register.filter
def vimeo_embed(url):
    """Convert Vimeo URL to embed URL"""
    if 'vimeo.com/' in url and '/video/' not in url:
        video_id = url.split('vimeo.com/')[-1].split('?')[0]
        return f'https://player.vimeo.com/video/{video_id}'
    return url

@register.filter
def replace(value, arg):
    """Replace substring in string (old,new)"""
    try:
        old, new = arg.split(',')
        return value.replace(old, new)
    except:
        return value

@register.filter
def learning_objectives_as_list(value):
    """Convert learning objectives string to list"""
    if value:
        return [obj.strip() for obj in value.split('\n') if obj.strip()]
    return []