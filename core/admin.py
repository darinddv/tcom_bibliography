from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.shortcuts import redirect
from django.urls import path

from core.services.doi_import import import_from_doi

from core.models.controlled_vocabulary import ControlledTerm
from core.models.publications import Publication
from core.models.users import UserProfile
from core.models.workflow import WorkflowTransition, PublicationAssignment
from core.models.extraction import ExtractionRecord
from core.models.study_profile import StudyProfile
from core.models.assessment import AssessmentToolUsage, OutcomeDomain
from core.models.extraction_review import ExtractionReview



# --- User ---

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'


class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]

    def get_inlines(self, request, obj):
        if obj is None:
            return []
        return [UserProfileInline]


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


# --- Controlled Vocabulary ---

@admin.register(ControlledTerm)
class ControlledTermAdmin(admin.ModelAdmin):
    list_display = ['label', 'abbreviation', 'category', 'is_approved', 'suggested_by']
    list_filter = ['category', 'is_approved']
    search_fields = ['label', 'abbreviation']
    list_editable = ['is_approved']
    ordering = ['category', 'label']


# --- Publications ---

@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ['title', 'year', 'journal', 'publication_type', 'inclusion_status', 'metadata_source']
    list_filter = ['inclusion_status', 'publication_type', 'metadata_source', 'year']
    search_fields = ['title', 'doi', 'abstract']
    readonly_fields = ['raw_metadata', 'metadata_source', 'created_at', 'updated_at']
    change_list_template = 'admin/publication_changelist.html'
    fieldsets = [
        ('Identifiers', {
            'fields': ['doi', 'pmid', 'arxiv_id']
        }),
        ('Bibliographic', {
            'fields': ['title', 'abstract', 'year', 'journal', 'volume', 'issue',
                       'pages', 'language', 'publication_type']
        }),
        ('Curation', {
            'fields': ['inclusion_status', 'exclusion_reason', 'curation_notes']
        }),
        ('Import', {
            'fields': ['metadata_source', 'raw_metadata'],
            'classes': ['collapse'],
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse'],
        }),
    ]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-doi/', self.admin_site.admin_view(self.import_doi_view), name='import_doi'),
        ]
        return custom_urls + urls

    def import_doi_view(self, request):
        if request.method == 'POST':
            doi = request.POST.get('doi', '').strip()
            if doi:
                try:
                    pub, created = import_from_doi(doi)
                    if created:
                        self.message_user(
                            request,
                            f'Successfully imported: {pub.title[:80]}',
                            messages.SUCCESS
                        )
                    else:
                        self.message_user(
                            request,
                            f'Already exists: {pub.title[:80]}',
                            messages.WARNING
                        )
                except Exception as e:
                    self.message_user(request, f'Import failed: {e}', messages.ERROR)
        return redirect('admin:core_publication_changelist')
    



# --- Workflow ---

@admin.register(WorkflowTransition)
class WorkflowTransitionAdmin(admin.ModelAdmin):
    list_display = ['publication', 'from_state', 'to_state', 'actor', 'is_system_action', 'timestamp']
    list_filter = ['to_state', 'is_system_action']
    search_fields = ['publication__title']
    readonly_fields = ['publication', 'from_state', 'to_state', 'actor', 'timestamp', 'comment', 'is_system_action']
    ordering = ['-timestamp']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PublicationAssignment)
class PublicationAssignmentAdmin(admin.ModelAdmin):
    list_display = ['publication', 'assigned_to', 'assigned_by', 'assigned_at', 'completed_at']
    list_filter = ['assigned_at']
    search_fields = ['publication__title', 'assigned_to__username']
    readonly_fields = ['assigned_at']


class OutcomeDomainInline(admin.TabularInline):
    model = OutcomeDomain
    extra = 1
    fields = ['domain', 'direction', 'notes']


class AssessmentToolUsageInline(admin.TabularInline):
    model = AssessmentToolUsage
    extra = 1
    fields = ['tool', 'used_as', 'sample_size', 'age_range_min', 'age_range_max', 'population_type', 'notes']


class StudyProfileInline(admin.StackedInline):
    model = StudyProfile
    extra = 0
    fields = ['study_design', 'overall_sample_size', 'setting', 'country', 'notes']


@admin.register(ExtractionRecord)
class ExtractionRecordAdmin(admin.ModelAdmin):
    list_display = ['publication', 'reviewer', 'reviewer_type', 'llm_model', 'status', 'created_at']
    list_filter = ['reviewer_type', 'status']
    search_fields = ['publication__title', 'reviewer__username', 'llm_model']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [StudyProfileInline, AssessmentToolUsageInline]




@admin.register(ExtractionReview)
class ExtractionReviewAdmin(admin.ModelAdmin):
    list_display = ['extraction', 'submitted_by', 'reviewer', 'decision', 'submitted_at', 'reviewed_at']
    list_filter = ['decision']
    search_fields = ['extraction__publication__title', 'submitted_by__username', 'reviewer__username']
    readonly_fields = ['submitted_at']