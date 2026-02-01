from django.urls import path
from django.contrib.auth.decorators import login_required
from . import views

app_name = 'questionnaires'

urlpatterns = [
    # Questionnaire URLs
    path('', views.QuestionnaireListView.as_view(), name='questionnaire_list'),
    path('create/', views.QuestionnaireCreateView.as_view(), name='questionnaire_create'),
    path('builder/', views.simple_questionnaire_builder, name='simple_questionnaire_builder'),
    path('<int:pk>/', views.QuestionnaireDetailView.as_view(), name='questionnaire_detail'),
    path('<int:pk>/update/', views.QuestionnaireUpdateView.as_view(), name='questionnaire_update'),
    path('<int:pk>/delete/', views.QuestionnaireDeleteView.as_view(), name='questionnaire_delete'),
    
    # Question URLs
    path('questions/create/<int:questionnaire_id>/', views.QuestionCreateView.as_view(), name='question_create'),
    path('questions/<int:pk>/update/', views.QuestionUpdateView.as_view(), name='question_update'),
    path('questions/<int:pk>/delete/', views.QuestionDeleteView.as_view(), name='question_delete'),
    
    # Response URLs
    path('responses/', views.ResponseListView.as_view(), name='response_list'),
    path('responses/<int:pk>/', views.ResponseDetailView.as_view(), name='response_detail'),
    path('responses/<int:pk>/delete/', views.ResponseDeleteView.as_view(), name='response_delete'),
    
    # API URLs
    path('api/questions/order/', views.update_question_order, name='update_question_order'),

    # Public flow (optional)
    path('<int:pk>/start/', views.questionnaire_start, name='questionnaire_start'),
    path('thank-you/<int:pk>/', views.questionnaire_thank_you, name='questionnaire_thank_you'),
]
