from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import (
    ListView, CreateView, UpdateView, DeleteView, DetailView
)
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required

from .models import Questionnaire, Question, QuestionOption, Response, Answer
from .forms import QuestionnaireForm, QuestionForm, ResponseForm

# Questionnaire Views
class QuestionnaireListView(LoginRequiredMixin, ListView):
    model = Questionnaire
    template_name = 'questionnaires/questionnaire_list.html'
    context_object_name = 'questionnaires'
    paginate_by = 10
    
    def get_queryset(self):
        return Questionnaire.objects.filter(is_active=True).order_by('-created_at')

class QuestionnaireCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Questionnaire
    form_class = QuestionnaireForm
    template_name = 'questionnaires/questionnaire_form.html'
    
    def test_func(self):
        return self.request.user.is_staff
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Questionnaire created successfully.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('questionnaires:questionnaire_detail', kwargs={'pk': self.object.pk})

class QuestionnaireUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Questionnaire
    form_class = QuestionnaireForm
    template_name = 'questionnaires/questionnaire_form.html'
    
    def test_func(self):
        return self.request.user.is_staff
    
    def form_valid(self, form):
        messages.success(self.request, 'Questionnaire updated successfully.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('questionnaires:questionnaire_detail', kwargs={'pk': self.object.pk})

class QuestionnaireDetailView(LoginRequiredMixin, DetailView):
    model = Questionnaire
    template_name = 'questionnaires/questionnaire_detail.html'
    context_object_name = 'questionnaire'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['questions'] = self.object.questions.all().order_by('display_order')
        return context

class QuestionnaireDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Questionnaire
    template_name = 'questionnaires/questionnaire_confirm_delete.html'
    success_url = reverse_lazy('questionnaires:questionnaire_list')
    
    def test_func(self):
        return self.request.user.is_staff
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Questionnaire deleted successfully.')
        return super().delete(request, *args, **kwargs)

# Question Views
class QuestionCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Question
    form_class = QuestionForm
    template_name = 'questionnaires/question_form.html'
    
    def test_func(self):
        return self.request.user.is_staff
    
    def get_initial(self):
        initial = super().get_initial()
        questionnaire_id = self.kwargs.get('questionnaire_id')
        if questionnaire_id:
            initial['questionnaire'] = get_object_or_404(Questionnaire, id=questionnaire_id)
        return initial
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        questionnaire_id = self.kwargs.get('questionnaire_id')
        if questionnaire_id:
            context['questionnaire'] = get_object_or_404(Questionnaire, id=questionnaire_id)
        return context
    
    def form_valid(self, form):
        questionnaire_id = self.kwargs.get('questionnaire_id')
        questionnaire = get_object_or_404(Questionnaire, id=questionnaire_id)
        form.instance.questionnaire = questionnaire
        
        # Set the display order to be the next available number
        last_question = (
            Question.objects.filter(questionnaire=questionnaire)
            .order_by('-display_order')
            .first()
        )
        form.instance.display_order = (last_question.display_order + 1) if last_question else 1
        
        messages.success(self.request, 'Question added successfully.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('questionnaires:questionnaire_detail', 
                          kwargs={'pk': self.object.questionnaire.id})

class QuestionUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Question
    form_class = QuestionForm
    template_name = 'questionnaires/question_form.html'
    
    def test_func(self):
        return self.request.user.is_staff
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['questionnaire'] = self.object.questionnaire
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Question updated successfully.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('questionnaires:questionnaire_detail', 
                          kwargs={'pk': self.object.questionnaire.id})

class QuestionDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Question
    template_name = 'questionnaires/question_confirm_delete.html'
    
    def test_func(self):
        return self.request.user.is_staff
    
    def get_success_url(self):
        questionnaire_id = self.object.questionnaire.id
        return reverse_lazy('questionnaires:questionnaire_detail', 
                          kwargs={'pk': questionnaire_id})
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Question deleted successfully.')
        return super().delete(request, *args, **kwargs)

# Response Views
class ResponseListView(LoginRequiredMixin, ListView):
    model = Response
    template_name = 'questionnaires/response_list.html'
    context_object_name = 'responses'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Response.objects.select_related('questionnaire', 'respondent')
        
        # Filter by questionnaire if specified
        questionnaire_id = self.request.GET.get('questionnaire')
        if questionnaire_id:
            queryset = queryset.filter(questionnaire_id=questionnaire_id)
            
        # Filter by respondent if specified
        respondent_id = self.request.GET.get('respondent')
        if respondent_id:
            queryset = queryset.filter(respondent_id=respondent_id)
            
        return queryset.order_by('-submitted_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['questionnaires'] = Questionnaire.objects.filter(is_active=True)
        return context

class ResponseDetailView(LoginRequiredMixin, DetailView):
    model = Response
    template_name = 'questionnaires/response_detail.html'
    context_object_name = 'response'
    
    def get_queryset(self):
        return Response.objects.select_related('questionnaire', 'respondent')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['answers'] = self.object.answers.select_related('question')
        return context

class ResponseDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Response
    template_name = 'questionnaires/response_confirm_delete.html'
    
    def test_func(self):
        return self.request.user.is_staff or self.request.user == self.get_object().respondent
    
    def get_success_url(self):
        return reverse_lazy('questionnaires:response_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Response deleted successfully.')
        return super().delete(request, *args, **kwargs)

# API Views
@login_required
@require_http_methods(['POST'])
def update_question_order(request):
    try:
        question_order = request.POST.getlist('order[]')
        with transaction.atomic():
            for index, question_id in enumerate(question_order, start=1):
                Question.objects.filter(id=question_id).update(display_order=index)
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

# Public Views
def questionnaire_start(request, pk):
    questionnaire = get_object_or_404(Questionnaire, pk=pk, is_active=True)
    
    if request.method == 'POST':
        form = ResponseForm(questionnaire, request.POST)
        if form.is_valid():
            response = form.save(commit=False)
            response.questionnaire = questionnaire
            if request.user.is_authenticated:
                response.respondent = request.user
            response.save()
            form.save_answers()
            return redirect('questionnaires:questionnaire_thank_you', pk=response.pk)
    else:
        form = ResponseForm(questionnaire)
    
    return render(request, 'questionnaires/questionnaire_form.html', {
        'questionnaire': questionnaire,
        'form': form,
    })

def questionnaire_thank_you(request, pk):
    response = get_object_or_404(Response, pk=pk)
    return render(request, 'questionnaires/thank_you.html', {
        'response': response,
    })
