from django.urls import path
from contributor import views

app_name = 'contributor'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('publications/', views.publication_list, name='publication_list'),
    path('publications/<int:pk>/', views.publication_detail, name='publication_detail'),
    path('publications/<int:pk>/assign/', views.assign_to_me, name='assign_to_me'),
    path('publications/<int:pk>/extract/', views.extraction_form, name='extraction_form'),
    path('publications/<int:pk>/extract/add-tool/', views.add_tool_usage, name='add_tool_usage'),
    path('publications/<int:pk>/extract/add-outcome/<int:tool_usage_id>/', views.add_outcome_domain, name='add_outcome_domain'),
    path('publications/<int:pk>/extract/delete-tool/<int:tool_usage_id>/', views.delete_tool_usage, name='delete_tool_usage'),
    path('publications/<int:pk>/extract/delete-outcome/<int:outcome_id>/', views.delete_outcome_domain, name='delete_outcome_domain'),
    path('review/', views.review_queue, name='review_queue'),
    path('profile/', views.profile, name='profile'),
    path('logout/', views.logout_view, name='logout'),
    path('review/<int:review_id>/', views.review_detail, name='review_detail'),
    path('publications/<int:pk>/unassign/', views.unassign_me, name='unassign_me'),
    path('publications/<int:pk>/extractions/<int:extraction_id>/', views.extraction_detail, name='extraction_detail'),
]