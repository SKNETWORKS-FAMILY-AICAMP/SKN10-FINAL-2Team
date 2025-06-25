from django import template
from django.utils.safestring import mark_safe
import markdown

register = template.Library()

@register.filter(name='markdown_to_html')
def markdown_to_html(value):
    """
    Markdown 텍스트를 HTML로 변환하는 필터
    """
    if not value:
        return ''
    
    # Markdown을 HTML로 변환
    html = markdown.markdown(value, extensions=['extra'])
    return mark_safe(html) 