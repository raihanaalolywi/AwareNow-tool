# account/templatetags/youtube_filters.py
from django import template
import re

register = template.Library()

@register.filter
def youtube_embed(url):
    """
    Convert any YouTube URL to embed format.
    
    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - https://youtube.com/shorts/VIDEO_ID
    - URLs with extra parameters
    """
    if not url:
        return ""
    
    # Extract video ID using regex
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/watch\?.*v=([a-zA-Z0-9_-]{11})',
        r'youtu\.be\/([a-zA-Z0-9_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            # Return embed URL with safe parameters
            return f"https://www.youtube.com/embed/{video_id}?rel=0&modestbranding=1"
    
    return url  # Return original if no match