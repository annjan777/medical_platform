from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()

class Questionnaire(models.Model):
    """Model representing a questionnaire or form template."""
    
    # Questionnaire status choices
    STATUS_DRAFT = 'draft'
    STATUS_ACTIVE = 'active'
    STATUS_ARCHIVED = 'archived'
    
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_ARCHIVED, 'Archived'),
    ]
    
    # Questionnaire types
    TYPE_SCREENING = 'screening'
    TYPE_ASSESSMENT = 'assessment'
    TYPE_FOLLOW_UP = 'follow_up'
    TYPE_CUSTOM = 'custom'
    
    TYPE_CHOICES = [
        (TYPE_SCREENING, 'Screening'),
        (TYPE_ASSESSMENT, 'Assessment'),
        (TYPE_FOLLOW_UP, 'Follow-up'),
        (TYPE_CUSTOM, 'Custom'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    version = models.CharField(max_length=20, default='1.0')
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default=STATUS_DRAFT
    )
    questionnaire_type = models.CharField(
        max_length=20, 
        choices=TYPE_CHOICES,
        default=TYPE_CUSTOM
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_questionnaires'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'questionnaire'
        verbose_name_plural = 'questionnaires'
    
    def __str__(self):
        return f"{self.title} (v{self.version})"
    
    def get_absolute_url(self):
        return reverse('questionnaires:detail', args=[str(self.id)])
    
    def get_questions(self):
        """Return all questions for this questionnaire ordered by display order."""
        return self.questions.all().order_by('display_order')
    
    def is_complete(self, response):
        """Check if all required questions have been answered in the given response."""
        answered_questions = response.answers.values_list('question_id', flat=True)
        return not self.questions.filter(
            is_required=True
        ).exclude(
            id__in=answered_questions
        ).exists()


class Question(models.Model):
    """Model representing a question in a questionnaire."""
    
    # Question types
    TYPE_TEXT = 'text'
    TYPE_TEXTAREA = 'textarea'
    TYPE_RADIO = 'radio'
    TYPE_CHECKBOX = 'checkbox'
    TYPE_SELECT = 'select'
    TYPE_RATING = 'rating'
    TYPE_DATE = 'date'
    TYPE_EMAIL = 'email'
    TYPE_NUMBER = 'number'
    TYPE_FILE = 'file'
    
    QUESTION_TYPES = [
        (TYPE_TEXT, 'Short Text'),
        (TYPE_TEXTAREA, 'Long Text'),
        (TYPE_RADIO, 'Multiple Choice (Single Answer)'),
        (TYPE_CHECKBOX, 'Multiple Choice (Multiple Answers)'),
        (TYPE_SELECT, 'Dropdown'),
        (TYPE_RATING, 'Rating Scale'),
        (TYPE_DATE, 'Date'),
        (TYPE_EMAIL, 'Email'),
        (TYPE_NUMBER, 'Number'),
        (TYPE_FILE, 'File Upload'),
    ]
    
    questionnaire = models.ForeignKey(
        Questionnaire,
        on_delete=models.CASCADE,
        related_name='questions'
    )
    text = models.TextField()
    help_text = models.TextField(blank=True)
    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPES,
        default=TYPE_TEXT
    )
    is_required = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Conditional logic fields
    depends_on_question = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dependent_questions'
    )
    depends_on_value = models.TextField(blank=True, null=True)
    
    # For file uploads
    allowed_file_types = models.CharField(max_length=200, blank=True)
    max_file_size = models.PositiveIntegerField(
        default=5,  # 5MB default
        help_text='Maximum file size in MB'
    )
    
    # For number fields
    min_value = models.FloatField(null=True, blank=True)
    max_value = models.FloatField(null=True, blank=True)
    
    # For rating scales
    min_label = models.CharField(max_length=50, blank=True)
    max_label = models.CharField(max_length=50, blank=True)
    
    class Meta:
        ordering = ['display_order', 'created_at']
        verbose_name = 'question'
        verbose_name_plural = 'questions'
    
    def __str__(self):
        return f"{self.questionnaire.title} - {self.text[:50]}..."
    
    def get_absolute_url(self):
        return reverse('questionnaires:question_detail', args=[str(self.id)])
    
    def has_options(self):
        """Check if this question type should have options."""
        return self.question_type in [
            self.TYPE_RADIO, 
            self.TYPE_CHECKBOX, 
            self.TYPE_SELECT
        ]
    
    def get_options(self):
        """Get all options for this question."""
        return self.options.all().order_by('display_order')
    
    def validate_answer(self, value):
        """Validate the answer value based on question type."""
        if self.is_required and not value:
            return False
            
        if not value:  # If not required and no value, it's valid
            return True
            
        if self.question_type == self.TYPE_EMAIL:
            from django.core.validators import validate_email
            try:
                validate_email(value)
                return True
            except:
                return False
                
        elif self.question_type == self.TYPE_NUMBER:
            try:
                num = float(value)
                if self.min_value is not None and num < self.min_value:
                    return False
                if self.max_value is not None and num > self.max_value:
                    return False
                return True
            except (ValueError, TypeError):
                return False
                
        return True


class QuestionOption(models.Model):
    """Model representing an option for a multiple choice question."""
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='options'
    )
    text = models.CharField(max_length=200)
    value = models.CharField(max_length=100)
    display_order = models.PositiveIntegerField(default=0)
    option_image = models.ImageField(
        upload_to='question_options/',
        null=True,
        blank=True,
        help_text='Optional image for this option'
    )
    is_image_primary = models.BooleanField(
        default=False,
        help_text='Display image instead of text'
    )
    
    class Meta:
        ordering = ['display_order']
        verbose_name = 'question option'
        verbose_name_plural = 'question options'
    
    def __str__(self):
        return self.text
    
    def get_display_content(self):
        """Return the appropriate display content (text or image)."""
        if self.is_image_primary and self.option_image:
            return {
                'type': 'image',
                'content': self.option_image.url,
                'alt_text': self.text
            }
        else:
            return {
                'type': 'text',
                'content': self.text,
                'alt_text': None
            }


class Response(models.Model):
    """Model representing a respondent's response to a questionnaire."""
    questionnaire = models.ForeignKey(
        Questionnaire,
        on_delete=models.CASCADE,
        related_name='responses'
    )
    respondent = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='questionnaire_responses'
    )
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='questionnaire_responses',
        null=True,
        blank=True
    )
    session = models.ForeignKey(
        'screening.ScreeningSession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='questionnaire_responses'
    )
    is_complete = models.BooleanField(default=False)
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-submitted_at', '-started_at']
        verbose_name = 'response'
        verbose_name_plural = 'responses'
    
    def __str__(self):
        return f"Response to {self.questionnaire} by {self.respondent or 'Anonymous'}"
    
    def get_absolute_url(self):
        return reverse('questionnaires:response_detail', args=[str(self.id)])
    
    def get_answers(self):
        """Get all answers for this response."""
        return {a.question_id: a for a in self.answers.all()}
    
    def get_answer(self, question):
        """Get the answer for a specific question in this response."""
        try:
            return self.answers.get(question=question)
        except Answer.DoesNotExist:
            return None


class Answer(models.Model):
    """Model representing an answer to a single question in a response."""
    response = models.ForeignKey(
        Response,
        on_delete=models.CASCADE,
        related_name='answers'
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='answers'
    )
    text_answer = models.TextField(blank=True)
    number_answer = models.FloatField(null=True, blank=True)
    date_answer = models.DateField(null=True, blank=True)
    file_answer = models.FileField(upload_to='questionnaire_answers/%Y/%m/%d/', null=True, blank=True)
    option_answer = models.ManyToManyField(QuestionOption, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['question__display_order']
        unique_together = ('response', 'question')
        verbose_name = 'answer'
        verbose_name_plural = 'answers'
    
    def __str__(self):
        return f"Answer to '{self.question.text[:50]}...' in {self.response}"
    
    def get_value(self):
        """Get the appropriate value based on question type."""
        if self.question.question_type == Question.TYPE_RADIO:
            return self.option_answer.first().value if self.option_answer.exists() else None
        elif self.question.question_type == Question.TYPE_CHECKBOX:
            return [opt.value for opt in self.option_answer.all()]
        elif self.question.question_type == Question.TYPE_NUMBER:
            return self.number_answer
        elif self.question.question_type == Question.TYPE_DATE:
            return self.date_answer
        elif self.question.question_type == Question.TYPE_FILE:
            return self.file_answer
        else:
            return self.text_answer
