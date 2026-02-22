import re

with open("templates/screening/session_list.html", "r") as f:
    content = f.read()

# Replace the status options
status_options = [
    ("scheduled", "Scheduled"),
    ("in_progress", "In Progress"),
    ("completed", "Completed"),
    ("cancelled", "Cancelled"),
    ("rescheduled", "Rescheduled")
]

old_status_block = re.search(r'<select name="status" class="form-select">.*?</select>', content, flags=re.DOTALL).group(0)

new_status_block = '<select name="status" class="form-select">\n                            <option value="">All Status</option>'
for val, label in status_options:
    new_status_block += f"""
                            {{% if request.GET.status == '{val}' %}}
                            <option value="{val}" selected>{label}</option>
                            {{% else %}}
                            <option value="{val}">{label}</option>
                            {{% endif %}}"""
new_status_block += '\n                        </select>'

content = content.replace(old_status_block, new_status_block)

# Replace the screening_type loop
old_type_loop = re.search(r'{% for type in screening_types %}.*?{% endfor %}', content, flags=re.DOTALL).group(0)

new_type_loop = """{% for type in screening_types %}
                            {% if request.GET.screening_type == type.id|stringformat:"s" %}
                            <option value="{{ type.id }}" selected>{{ type.name }}</option>
                            {% else %}
                            <option value="{{ type.id }}">{{ type.name }}</option>
                            {% endif %}
                            {% endfor %}"""

content = content.replace(old_type_loop, new_type_loop)

with open("templates/screening/session_list.html", "w") as f:
    f.write(content)

print("Patch applied successfully.")
