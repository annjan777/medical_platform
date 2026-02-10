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
        return self.questions.all().order_by('order')
    
    def is_complete(self, response):
        """Check if all required questions have been answered in the given response."""
        answered_questions = response.answers.values_list('question_id', flat=True)
        return not self.questions.filter(
            is_required=True
        ).exclude(
            id__in=answered_questions
        ).exists()


class Question(models.Model):
    """Simplified model for questionnaire questions."""
    
    # Question types as per requirements
    TYPE_YES_NO = 'yes_no'
    TYPE_TRUE_FALSE = 'true_false'
    TYPE_MULTIPLE_CHOICE = 'multiple_choice'
    TYPE_SHORT_ANSWER = 'short_answer'
    TYPE_ATTACHMENT = 'attachment'
    
    QUESTION_TYPES = [
        (TYPE_YES_NO, 'Yes/No'),
        (TYPE_TRUE_FALSE, 'True/False'),
        (TYPE_MULTIPLE_CHOICE, 'Multiple Choice'),
        (TYPE_SHORT_ANSWER, 'Short Answer'),
        (TYPE_ATTACHMENT, 'Attachment'),
    ]
    
    questionnaire = models.ForeignKey(Questionnaire, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    order = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['order']
    
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
        return self.options.all().order_by('order')
    
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
    """Options for multiple choice questions with image support."""
    
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=255, blank=True)  # Text option
    option_image = models.ImageField(upload_to='question_options/', blank=True, null=True)  # Image option
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        if self.text:
            return self.text
        elif self.option_image:
            return f"Image: {self.option_image.name}"
        return f"Option {self.id}"
    
    def get_display_content(self):
        """Return the appropriate content for display (text or image)."""
        if self.option_image:
            return {
                'type': 'image',
                'url': self.option_image.url,
                'alt': self.text or f"Option {self.id}"
            }
        else:
            return {
                'type': 'text',
                'content': self.text
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
        if self.patient:
            return f"Response to {self.questionnaire.title} by {self.patient.patient_id} - {self.patient.first_name} {self.patient.last_name}"
        elif self.respondent:
            return f"Response to {self.questionnaire.title} by {self.respondent.username}"
        else:
            return f"Response to {self.questionnaire.title} by Anonymous"
    
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
        ordering = ['question__order']
        unique_together = ('response', 'question')
        verbose_name = 'answer'
        verbose_name_plural = 'answers'
    
    def __str__(self):
        return f"Answer to '{self.question.text[:50]}...' in {self.response}"
    
    def get_value(self):
        """Get the appropriate value based on question type."""
        if self.question.question_type == Question.TYPE_MULTIPLE_CHOICE:
            return self.option_answer.first() if self.option_answer.exists() else None
        elif self.question.question_type in [Question.TYPE_YES_NO, Question.TYPE_TRUE_FALSE]:
            return self.text_answer
        elif self.question.question_type == Question.TYPE_SHORT_ANSWER:
            return self.text_answer
        elif self.question.question_type == Question.TYPE_ATTACHMENT:
            return self.file_answer
        else:
            return self.text_answer
