import re
import sys

filepath = '/Users/annjan/Desktop/cursor/medical_platform/templates/questionnaires/simple_questionnaire_display.html'
with open(filepath, 'r') as f:
    content = f.read()

# Fix the broken {% if %} tags
pattern = r'\{%\s*if\s+question\.is_required\s*\n\s*%\}required\s*\{%\s*endif\s*%\}'
content = re.sub(pattern, '{% if question.is_required %}required{% endif %}', content)

# But also we need to add line breaks to the <input> tags so they don't get auto-formatted
content = re.sub(
    r'<input type="radio" name="question_\{\{\s*question\.id\s*\}\}" value="([^"]+)" \{% if question\.is_required %\}required\{% endif %\}>',
    r'<input type="radio"\n                               name="question_{{ question.id }}"\n                               value="\1"\n                               {% if question.is_required %}required{% endif %}>',
    content
)

content = re.sub(
    r'<textarea name="question_\{\{\s*question\.id\s*\}\}" class="form-textarea"\s*\n\s*placeholder="Enter your answer here..." \{% if question\.is_required %\}required\{% endif %\}>\s*</textarea>',
    r'<textarea name="question_{{ question.id }}" class="form-textarea"\n                        placeholder="Enter your answer here..."\n                        {% if question.is_required %}required{% endif %}></textarea>',
    content
)

content = re.sub(
    r'accept="([^"]+)" \{% if question\.is_required %\}required\{% endif %\}>',
    r'accept="\1"\n                                {% if question.is_required %}required{% endif %}>',
    content
)

with open(filepath, 'w') as f:
    f.write(content)
