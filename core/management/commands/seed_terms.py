from django.core.management.base import BaseCommand
from core.models.controlled_vocabulary import ControlledTerm


TERMS = {
    'assessment_tool': [
        ('Child and Adolescent Needs and Strengths', 'CANS'),
        ('Adult Needs and Strengths Assessment', 'ANSA'),
        ('Functional Assessment for Children and Teens', 'FACT'),
        ('Child and Adolescent Functional Assessment Scale', 'CAFAS'),
        ('Child and Adolescent Service Intensity Instrument', 'CASII'),
        ('Child Severity of Psychiatric Illness', 'CSPI'),
        ('Child and Adolescent Trauma Screen', 'CATS'),
        ('Functional Assessment Rating Scale', 'FARS'),
        ('Pediatric Symptom Checklist', 'PSC'),
        ('Strengths and Difficulties Questionnaire', 'SDQ'),
        ('Columbia Impairment Scale', 'CIS'),
        ('Ohio Scales', 'Ohio'),
        ('Family Assessment Device', 'FAD'),
    ],

    'study_design': [
        ('Observational / Cross-sectional', ''),
        ('Longitudinal / Cohort', ''),
        ('Quasi-experimental', ''),
        ('Randomized Controlled Trial', 'RCT'),
        ('Case-control', ''),
        ('Mixed methods', ''),
        ('Secondary data analysis', ''),
        ('Systematic review / Meta-analysis', ''),
        ('Program evaluation', ''),
        ('Psychometric / Validation study', ''),
    ],

    'setting': [
        ('Public child welfare agency', ''),
        ('Wraparound services', ''),
        ('Behavioral health / Mental health', ''),
        ('Substance use treatment', ''),
        ('Legal / Court / Justice setting', ''),
        ('Inpatient / Hospital', ''),
        ('Outpatient clinic', ''),
        ('School', ''),
        ('Residential treatment', ''),
        ('Community-based', ''),
        ('Laboratory / Experimental', ''),
        ('Multi-site', ''),
    ],

    'population_type': [
        ('Children and adolescents (general)', ''),
        ('Children in child welfare', ''),
        ('Youth with serious emotional disturbance', 'SED'),
        ('Youth in juvenile justice', ''),
        ('Youth with substance use disorders', ''),
        ('Youth with trauma history', ''),
        ('Transition-age youth', 'TAY'),
        ('Adults with serious mental illness', 'SMI'),
        ('Military / Veteran families', ''),
        ('Mixed / Multi-population', ''),
    ],

    'outcome_domain': [
        ('Behavioral / Emotional functioning', ''),
        ('Strengths', ''),
        ('Trauma / PTSD symptoms', ''),
        ('Substance use', ''),
        ('Risk behaviors', ''),
        ('Service utilization', ''),
        ('Placement stability', ''),
        ('School functioning', ''),
        ('Family functioning', ''),
        ('Life domain functioning', ''),
        ('Tool reliability', ''),
        ('Tool validity', ''),
        ('Predictive utility', ''),
        ('Clinical change / Outcomes', ''),
    ],

    'administration_context': [
        ('Intake / Baseline', ''),
        ('Discharge', ''),
        ('Follow-up', ''),
        ('Cross-sectional (single timepoint)', ''),
        ('Multiple timepoints', ''),
        ('Reassessment / Periodic review', ''),
    ],

    'statistical_method': [
        ('General linear model / Multiple regression', 'GLM'),
        ('Mixed effects / Multilevel model', 'MLM'),
        ('Logistic regression', ''),
        ('Survival analysis / Cox regression', ''),
        ('Structural equation modeling', 'SEM'),
        ('Latent class analysis', 'LCA'),
        ('Latent growth curve', 'LGC'),
        ('Decision tree / Random forest', ''),
        ('Neural network', ''),
        ('Confirmatory factor analysis', 'CFA'),
        ('Exploratory factor analysis', 'EFA'),
        ('Item response theory', 'IRT'),
        ('Descriptive statistics only', ''),
        ('Propensity score matching', 'PSM'),
        ('Difference-in-differences', 'DiD'),
    ],

    'predictor_category': [
        ('Child demographics', ''),
        ('Parent / Caregiver demographics', ''),
        ('Strengths', ''),
        ('Functional impairment', ''),
        ('Behavioral / Emotional needs', ''),
        ('Traumatic experiences', ''),
        ('Risk behaviors', ''),
        ('Agency characteristics', ''),
        ('Caseworker characteristics', ''),
        ('Length of stay / Time', ''),
        ('Prior child welfare involvement', ''),
        ('Diagnosis / Clinical status', ''),
        ('Service intensity / Type', ''),
    ],

    'feedback_category': [
        ('Incorrect tool categorization', ''),
        ('Missing outcome data', ''),
        ('Sample size unclear', ''),
        ('Study design misclassified', ''),
        ('Statistical method incorrect', ''),
        ('Outcome direction unclear', ''),
        ('Country / Setting missing', ''),
        ('Inclusion criteria not captured', ''),
    ],
}


class Command(BaseCommand):
    help = 'Seed controlled vocabulary terms for the TCOM bibliography.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--approve',
            action='store_true',
            help='Mark all seeded terms as approved immediately.',
        )

    def handle(self, *args, **options):
        approve = options['approve']
        created_count = 0
        skipped_count = 0

        for category, terms in TERMS.items():
            for label, abbreviation in terms:
                obj, created = ControlledTerm.objects.get_or_create(
                    category=category,
                    label=label,
                    defaults={
                        'abbreviation': abbreviation,
                        'is_approved': approve,
                    }
                )
                if created:
                    created_count += 1
                    self.stdout.write(f'  + {category}: {label}')
                else:
                    skipped_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. {created_count} terms created, {skipped_count} already existed.'
        ))
        if not approve:
            self.stdout.write(
                self.style.WARNING(
                    'Terms were seeded as unapproved. Run with --approve to mark all as approved, '
                    'or approve them individually in Admin.'
                )
            )