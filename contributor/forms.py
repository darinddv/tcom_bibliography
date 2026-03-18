from django import forms
from core.models.study_profile import StudyProfile, US_STATES
from core.models.study_demographics import StudyDemographics
from core.models.risk_of_bias import RiskOfBiasAssessment, RiskOfBiasDomain
from core.models.statistical_method import StatisticalMethod
from core.models.predictor import PredictorCovariate
from core.models.assessment import AssessmentToolUsage, OutcomeDomain
from core.models.controlled_vocabulary import ControlledTerm


def approved_terms(category):
    return ControlledTerm.objects.filter(category=category, is_approved=True)


def ts(placeholder):
    """Shorthand for Tom Select widget attrs."""
    return {'class': 'form-select ts-select', 'data-placeholder': placeholder}


def fc():
    """Shorthand for standard form-control attrs."""
    return {'class': 'form-control'}


def fc_rows(n):
    """Shorthand for textarea attrs."""
    return {'class': 'form-control', 'rows': n}


class StudyProfileForm(forms.ModelForm):
    class Meta:
        model = StudyProfile
        fields = [
            'study_design', 'study_duration_years', 'follow_up_duration',
            'overall_sample_size', 'inclusion_criteria', 'exclusion_criteria',
            'country', 'us_state', 'setting',
            'funding_source', 'conflicts_of_interest',
            'notes',
        ]
        widgets = {
            'study_duration_years': forms.NumberInput(attrs={**fc(), 'step': '0.1'}),
            'follow_up_duration': forms.TextInput(attrs=fc()),
            'overall_sample_size': forms.NumberInput(attrs=fc()),
            'inclusion_criteria': forms.Textarea(attrs=fc_rows(3)),
            'exclusion_criteria': forms.Textarea(attrs=fc_rows(3)),
            'country': forms.TextInput(attrs=fc()),
            'us_state': forms.Select(attrs=ts('Select state...')),
            'funding_source': forms.Select(attrs={'class': 'form-select'}),
            'conflicts_of_interest': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs=fc_rows(3)),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['study_design'].queryset = approved_terms('study_design')
        self.fields['study_design'].widget.attrs.update(ts('Select study design...'))
        self.fields['setting'].queryset = approved_terms('setting')
        self.fields['setting'].widget.attrs.update(ts('Select setting...'))
        for field in self.fields.values():
            field.required = False


class StudyDemographicsForm(forms.ModelForm):
    class Meta:
        model = StudyDemographics
        fields = [
            'percent_female', 'percent_male',
            'age_range_min', 'age_range_max', 'age_notes',
            'race_distribution', 'notes',
        ]
        widgets = {
            'percent_female': forms.NumberInput(attrs={**fc(), 'step': '0.1', 'min': '0', 'max': '100'}),
            'percent_male': forms.NumberInput(attrs={**fc(), 'step': '0.1', 'min': '0', 'max': '100'}),
            'age_range_min': forms.NumberInput(attrs=fc()),
            'age_range_max': forms.NumberInput(attrs=fc()),
            'age_notes': forms.TextInput(attrs=fc()),
            'race_distribution': forms.Textarea(attrs=fc_rows(3)),
            'notes': forms.Textarea(attrs=fc_rows(2)),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False


class RiskOfBiasForm(forms.ModelForm):
    class Meta:
        model = RiskOfBiasAssessment
        fields = ['framework', 'overall_rating', 'notes']
        widgets = {
            'framework': forms.Select(attrs={'class': 'form-select'}),
            'overall_rating': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs=fc_rows(2)),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False


class RiskOfBiasDomainForm(forms.ModelForm):
    class Meta:
        model = RiskOfBiasDomain
        fields = ['domain_name', 'rating', 'notes']
        widgets = {
            'domain_name': forms.TextInput(attrs=fc()),
            'rating': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.TextInput(attrs=fc()),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False
        self.fields['domain_name'].required = True


class AssessmentToolUsageForm(forms.ModelForm):
    class Meta:
        model = AssessmentToolUsage
        fields = [
            'tool', 'used_as', 'sample_size',
            'age_range_min', 'age_range_max',
            'population_type', 'sample_descriptor',
            'administration_timing', 'scoring_method',
            'notes',
        ]
        widgets = {
            'used_as': forms.Select(attrs={'class': 'form-select'}),
            'sample_size': forms.NumberInput(attrs=fc()),
            'age_range_min': forms.NumberInput(attrs=fc()),
            'age_range_max': forms.NumberInput(attrs=fc()),
            'sample_descriptor': forms.Textarea(attrs=fc_rows(2)),
            'administration_timing': forms.Select(attrs={'class': 'form-select'}),
            'scoring_method': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs=fc_rows(2)),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tool'].queryset = approved_terms('assessment_tool')
        self.fields['tool'].widget.attrs.update(ts('Select tool...'))
        self.fields['population_type'].queryset = approved_terms('population_type')
        self.fields['population_type'].widget.attrs.update(ts('Select population type...'))
        for field in self.fields.values():
            field.required = False
        self.fields['tool'].required = True


class OutcomeDomainForm(forms.ModelForm):
    class Meta:
        model = OutcomeDomain
        fields = [
            'domain', 'direction',
            'outcome_metric', 'predictor', 'is_case_control',
            'effect_size_type', 'effect_size_value',
            'confidence_interval', 'p_value', 'significance',
            'result_description', 'notes',
        ]
        widgets = {
            'direction': forms.Select(attrs={'class': 'form-select'}),
            'outcome_metric': forms.TextInput(attrs=fc()),
            'predictor': forms.TextInput(attrs=fc()),
            'is_case_control': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'effect_size_type': forms.Select(attrs={'class': 'form-select'}),
            'effect_size_value': forms.NumberInput(attrs={**fc(), 'step': 'any'}),
            'confidence_interval': forms.TextInput(attrs=fc()),
            'p_value': forms.TextInput(attrs=fc()),
            'significance': forms.Select(attrs={'class': 'form-select'}),
            'result_description': forms.Textarea(attrs=fc_rows(2)),
            'notes': forms.Textarea(attrs=fc_rows(2)),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['domain'].queryset = approved_terms('outcome_domain')
        self.fields['domain'].widget.attrs.update(ts('Select outcome domain...'))
        for field in self.fields.values():
            field.required = False
        self.fields['domain'].required = True


class StatisticalMethodForm(forms.ModelForm):
    class Meta:
        model = StatisticalMethod
        fields = ['method_category', 'method_name', 'notes']
        widgets = {
            'method_category': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs=fc_rows(2)),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['method_name'].queryset = approved_terms('statistical_method')
        self.fields['method_name'].widget.attrs.update(ts('Select method...'))
        for field in self.fields.values():
            field.required = False


class PredictorCovariateForm(forms.ModelForm):
    class Meta:
        model = PredictorCovariate
        fields = ['category', 'description', 'notes']
        widgets = {
            'description': forms.Textarea(attrs=fc_rows(2)),
            'notes': forms.Textarea(attrs=fc_rows(2)),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = approved_terms('predictor_category')
        self.fields['category'].widget.attrs.update(ts('Select category...'))
        for field in self.fields.values():
            field.required = False