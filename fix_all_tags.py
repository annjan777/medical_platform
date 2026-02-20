import re

filepath = '/Users/annjan/Desktop/cursor/medical_platform/templates/questionnaires/simple_questionnaire_display.html'
with open(filepath, 'r') as f:
    text = f.read()

# Fix {{ ... \n ... }}
def remove_newlines_in_var(m):
    return '{{ ' + re.sub(r'\s+', ' ', m.group(1)).strip() + ' }}'
text = re.sub(r'\{\{([^}]+)\}\}', remove_newlines_in_var, text)

# Fix {% ... \n ... %}
def remove_newlines_in_tag(m):
    return '{% ' + re.sub(r'\s+', ' ', m.group(1)).strip() + ' %}'
text = re.sub(r'\{%([^%]+)%\}', remove_newlines_in_tag, text)

with open(filepath, 'w') as f:
    f.write(text)
