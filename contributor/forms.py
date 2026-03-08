from django import forms
from core.models.extraction import ExtractionRecord
from core.models.study_profile import StudyProfile
from core.models.assessment import AssessmentToolUsage, OutcomeDomain
from core.models.controlled_vocabulary import ControlledTerm


def approved_terms(category):
    """Helper to return approved ControlledTerm queryset for a given category."""
    return ControlledTerm.objects.filter(category=category, is_approved=True)


class StudyProfileForm(forms.ModelForm):
    class Meta:
        model = StudyProfile
        fields = ['study_design', 'overall_sample_size', 'setting', 'country', 'notes']
        widgets = {
            'overall_sample_size': forms.NumberInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['study_design'].queryset = approved_terms('study_design')
        self.fields['study_design'].widget.attrs['class'] = 'form-select'
        self.fields['setting'].queryset = approved_terms('setting')
        self.fields['setting'].widget.attrs['class'] = 'form-select'
        for field in self.fields.values():
            field.required = False


class AssessmentToolUsageForm(forms.ModelForm):
    class Meta:
        model = AssessmentToolUsage
        fields = ['tool', 'used_as', 'sample_size', 'age_range_min', 'age_range_max',
                  'population_type', 'notes']
        widgets = {
            'used_as': forms.Select(attrs={'class': 'form-select'}),
            'sample_size': forms.NumberInput(attrs={'class': 'form-control'}),
            'age_range_min': forms.NumberInput(attrs={'class': 'form-control'}),
            'age_range_max': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tool'].queryset = approved_terms('assessment_tool')
        self.fields['tool'].widget.attrs['class'] = 'form-select'
        self.fields['population_type'].queryset = approved_terms('population_type')
        self.fields['population_type'].widget.attrs['class'] = 'form-select'
        for field in self.fields.values():
            field.required = False
        self.fields['tool'].required = True


class OutcomeDomainForm(forms.ModelForm):
    class Meta:
        model = OutcomeDomain
        fields = ['domain', 'direction', 'notes']
        widgets = {
            'direction': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['domain'].queryset = approved_terms('outcome_domain')
        self.fields['domain'].widget.attrs['class'] = 'form-select'
        for field in self.fields.values():
            field.required = False
        self.fields['domain'].required = True