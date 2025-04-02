from django.urls import path
from . import views

urlpatterns = [
    path('add-employee/', views.add_employee_view, name='add_employee'),
    path('analysis/', views.analysis_view, name='analysis'),
    path('answer-survey/', views.answer_survey_view, name='answer_survey'),
    path('authentication-acc/', views.authentication_acc_view, name='authentication_acc'),
    path('authentication-org/', views.authentication_org_view, name='authentication_org'),
    path('create-acc/', views.create_acc_view, name='create_acc'),
    path('create-org/', views.create_org_view, name='create_org'),
    path('create-survey/', views.create_survey_view, name='create_survey'),
    path('index/', views.index_view, name='index'),
    path('', views.login_view, name='login'),
    path('my-org/', views.my_org_view, name='my_org'),
    path('my-results/', views.my_results_view, name='my_results'),
    path('my-surveys/', views.my_surveys_view, name='my_surveys'),
    path('publish-survey/', views.publish_survey_view, name='publish_survey'),
    path('settings-admin/', views.settings_admin_view, name='settings_admin'),
    path('settings-user/', views.settings_user_view, name='settings_user'),
    path('start-admin/', views.start_admin_view, name='start_admin'),
    path('start-user/', views.start_user_view, name='start_user'),
    path('survey-result/', views.survey_result_view, name='survey_result'),
    path('survey-status/', views.survey_status_view, name='survey_status'),
    path('unanswered-surveys/', views.unanswered_surveys_view, name='unanswered_surveys'),
]
