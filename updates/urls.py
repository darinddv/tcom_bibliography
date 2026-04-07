from django.urls import path
from contributor import views

app_name = 'contributor'

urlpatterns = [

    # --- Landing (root) ---
    path('', views.landing, name='landing'),

    # --- Public ---
    path('bibliography/', views.bibliography, name='bibliography'),
    path('bibliography/<int:pk>/', views.bibliography_detail, name='bibliography_detail'),
    path('analytics/', views.dashboard, name='analytics'),

    # --- Account ---
    path('accounts/register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('logout/', views.logout_view, name='logout'),

    # --- Contributor workflow ---
    path('work/', views.work, name='work'),
    path('publications/', views.publication_list, name='publication_list'),
    path('publications/import/', views.import_doi, name='import_doi'),
    path('publications/<int:pk>/', views.publication_detail, name='publication_detail'),
    path('publications/<int:pk>/assign/', views.assign_to_me, name='assign_to_me'),
    path('publications/<int:pk>/unassign/', views.unassign_me, name='unassign_me'),
    path('publications/<int:pk>/request-deletion/', views.request_deletion_view, name='request_deletion'),
    path('publications/<int:pk>/cancel-deletion/', views.cancel_deletion_view, name='cancel_deletion'),
    path('publications/<int:pk>/extractions/<int:extraction_id>/', views.extraction_detail, name='extraction_detail'),
    path('publications/<int:pk>/upload-pdf/', views.upload_pdf, name='upload_pdf'),
    path('publications/<int:pk>/delete-pdf/', views.delete_pdf, name='delete_pdf'),
    path('publications/<int:pk>/run-llm/', views.run_llm_extraction_view, name='run_llm_extraction'),

    # --- Extraction form (HTMX) ---
    path('publications/<int:pk>/extract/', views.extraction_form, name='extraction_form'),
    path('publications/<int:pk>/extract/llm/<int:extraction_id>/', views.extraction_form, name='llm_extraction_form'),
    path('publications/<int:pk>/extract/study-profile/', views.save_study_profile, name='save_study_profile'),
    path('publications/<int:pk>/extract/demographics/', views.save_demographics, name='save_demographics'),
    path('publications/<int:pk>/extract/risk-of-bias/', views.save_risk_of_bias, name='save_risk_of_bias'),
    path('publications/<int:pk>/extract/risk-of-bias/add-domain/', views.add_rob_domain, name='add_rob_domain'),
    path('publications/<int:pk>/extract/risk-of-bias/delete-domain/<int:domain_id>/', views.delete_rob_domain, name='delete_rob_domain'),
    path('publications/<int:pk>/extract/tools/', views.tools_section, name='tools_section'),
    path('publications/<int:pk>/extract/tools/add/', views.add_tool_usage, name='add_tool_usage'),
    path('publications/<int:pk>/extract/tools/<int:tool_usage_id>/delete/', views.delete_tool_usage, name='delete_tool_usage'),
    path('publications/<int:pk>/extract/tools/<int:tool_usage_id>/outcomes/add/', views.add_outcome_domain, name='add_outcome_domain'),
    path('publications/<int:pk>/extract/tools/<int:tool_usage_id>/outcomes/<int:outcome_id>/delete/', views.delete_outcome_domain, name='delete_outcome_domain'),
    path('publications/<int:pk>/extract/statistical-methods/add/', views.add_statistical_method, name='add_statistical_method'),
    path('publications/<int:pk>/extract/statistical-methods/<int:method_id>/delete/', views.delete_statistical_method, name='delete_statistical_method'),
    path('publications/<int:pk>/extract/predictors/add/', views.add_predictor, name='add_predictor'),
    path('publications/<int:pk>/extract/predictors/<int:predictor_id>/delete/', views.delete_predictor, name='delete_predictor'),
    path('publications/<int:pk>/extract/submit/', views.submit_extraction_view, name='submit_extraction'),

    # --- Review ---
    path('review/', views.review_queue, name='review_queue'),
    path('review/<int:review_id>/', views.review_detail, name='review_detail'),

    # --- Deletions ---
    path('deletions/', views.deletion_queue, name='deletion_queue'),
    path('deletions/<int:deletion_request_id>/resolve/', views.resolve_deletion_view, name='resolve_deletion'),
]
