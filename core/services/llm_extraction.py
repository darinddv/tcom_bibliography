import io
import json
import anthropic
from django.conf import settings

from core.models.publications import Publication
from core.models.extraction import ExtractionRecord
from core.models.study_profile import StudyProfile
from core.models.study_demographics import StudyDemographics
from core.models.risk_of_bias import RiskOfBiasAssessment, RiskOfBiasDomain
from core.models.statistical_method import StatisticalMethod
from core.models.predictor import PredictorCovariate
from core.models.assessment import AssessmentToolUsage, OutcomeDomain
from core.models.controlled_vocabulary import ControlledTerm
from core.models.extraction_review import ExtractionReview
from core.services.workflow import transition, get_current_state


def _get_approved_terms() -> dict:
    """
    Build a dictionary of approved controlled terms by category,
    formatted for inclusion in the LLM prompt.
    """
    terms = {}
    for term in ControlledTerm.objects.filter(is_approved=True).order_by('category', 'label'):
        if term.category not in terms:
            terms[term.category] = []
        terms[term.category].append({
            'id': term.pk,
            'label': term.label,
            'abbreviation': term.abbreviation,
        })
    return terms


def _extract_pdf_text(publication: Publication) -> str:
    """
    Extract text from the publication's PDF if one exists.
    Returns empty string if no PDF or extraction fails.
    Limits to first 50,000 characters to stay within context limits.
    """
    if not publication.pdf_file:
        return ''

    try:
        from pypdf import PdfReader

        with publication.pdf_file.open('rb') as f:
            pdf_bytes = f.read()

        reader = PdfReader(io.BytesIO(pdf_bytes))
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)

        full_text = '\n'.join(text_parts)
        return full_text[:50000]

    except Exception:
        return ''


def _build_prompt(publication: Publication, terms: dict, pdf_text: str = '') -> str:
    """
    Build the extraction prompt for Claude.
    Uses full PDF text if available, otherwise falls back to abstract.
    """
    terms_json = json.dumps(terms, indent=2)

    if pdf_text:
        text_section = f"""FULL PAPER TEXT (first 50,000 characters):
{pdf_text}"""
    else:
        text_section = f"""ABSTRACT:
{publication.abstract or 'No abstract available'}

NOTE: No full text available. Extract what you can from the title and abstract only."""

    return f"""You are a systematic review assistant specializing in child behavioral health research. Your task is to extract structured data from the following publication.

PUBLICATION METADATA:
Title: {publication.title}
Year: {publication.year or 'Not reported'}
Journal: {publication.journal or 'Not reported'}

{text_section}

CONTROLLED VOCABULARY:
The following are the only valid options for controlled fields. Always use the exact 'id' value when specifying a controlled term. If nothing matches, use null.

{terms_json}

INSTRUCTIONS:
- Extract all available information from the text above
- When information is not reported or cannot be determined, use null for numeric fields, empty string "" for text fields, and null for controlled term fields
- For assessment_tools, only include tools that are explicitly mentioned and studied in the paper
- For outcomes, capture what was actually measured and reported
- Be conservative — only extract what is clearly stated, do not infer

Respond with ONLY a valid JSON object matching this exact schema. Do not include any explanation or markdown formatting:

{{
  "study_profile": {{
    "study_design_id": <integer or null>,
    "study_duration_years": <float or null>,
    "follow_up_duration": "<string>",
    "overall_sample_size": <integer or null>,
    "inclusion_criteria": "<string>",
    "exclusion_criteria": "<string>",
    "country": "<string>",
    "us_state": "<two-letter code or empty string>",
    "setting_id": <integer or null>,
    "funding_source": "<government|industry|nonprofit|university|mixed|none|unclear or empty string>",
    "conflicts_of_interest": "<yes|no|unclear or empty string>",
    "notes": "<string>"
  }},
  "demographics": {{
    "percent_female": <float or null>,
    "percent_male": <float or null>,
    "age_range_min": <integer or null>,
    "age_range_max": <integer or null>,
    "age_notes": "<string>",
    "race_distribution": "<string>",
    "notes": "<string>"
  }},
  "risk_of_bias": {{
    "framework": "<rob2|robins_i|other or empty string>",
    "overall_rating": "<low|some_concerns|high|critical|unclear or empty string>",
    "notes": "<string>",
    "domains": [
      {{
        "domain_name": "<string>",
        "rating": "<low|some_concerns|high|na|unclear>",
        "notes": "<string>"
      }}
    ]
  }},
  "assessment_tools": [
    {{
      "tool_id": <integer>,
      "used_as": "<primary|secondary>",
      "sample_size": <integer or null>,
      "age_range_min": <integer or null>,
      "age_range_max": <integer or null>,
      "population_type_id": <integer or null>,
      "sample_descriptor": "<string>",
      "administration_timing": "<intake|discharge|follow_up|cross_sectional|multiple|other or empty string>",
      "scoring_method": "<total_score|subscale|cutoff|change_score|other or empty string>",
      "notes": "<string>",
      "outcomes": [
        {{
          "domain_id": <integer>,
          "direction": "<improvement|decline|mixed|null or empty string>",
          "outcome_metric": "<string>",
          "predictor": "<string>",
          "is_case_control": <boolean>,
          "effect_size_type": "<beta|or|rr|mean_diff|cohen_d|r|other or empty string>",
          "effect_size_value": <float or null>,
          "confidence_interval": "<string>",
          "p_value": "<string>",
          "significance": "<significant|not_significant|unclear or empty string>",
          "result_description": "<string>",
          "notes": "<string>"
        }}
      ]
    }}
  ],
  "statistical_methods": [
    {{
      "method_category": "<regression|classification|reliability|validity|descriptive|other>",
      "method_name_id": <integer or null>,
      "notes": "<string>"
    }}
  ],
  "predictors": [
    {{
      "category_id": <integer or null>,
      "description": "<string>",
      "notes": "<string>"
    }}
  ]
}}"""


def _create_extraction_objects(publication: Publication, data: dict) -> ExtractionRecord:
    """
    Create all extraction-related objects from the parsed LLM response.
    """
    llm_model = getattr(settings, 'ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')

    extraction = ExtractionRecord.objects.create(
        publication=publication,
        reviewer=None,
        reviewer_type='llm',
        llm_model=llm_model,
        status='submitted',
    )

    # --- Study Profile ---
    sp_data = data.get('study_profile', {})
    study_profile = StudyProfile.objects.create(
        extraction=extraction,
        study_design_id=sp_data.get('study_design_id'),
        study_duration_years=sp_data.get('study_duration_years'),
        follow_up_duration=sp_data.get('follow_up_duration', ''),
        overall_sample_size=sp_data.get('overall_sample_size'),
        inclusion_criteria=sp_data.get('inclusion_criteria', ''),
        exclusion_criteria=sp_data.get('exclusion_criteria', ''),
        country=sp_data.get('country', ''),
        us_state=sp_data.get('us_state', ''),
        setting_id=sp_data.get('setting_id'),
        funding_source=sp_data.get('funding_source', ''),
        conflicts_of_interest=sp_data.get('conflicts_of_interest', ''),
        notes=sp_data.get('notes', ''),
    )

    # --- Demographics ---
    demo_data = data.get('demographics', {})
    StudyDemographics.objects.create(
        study_profile=study_profile,
        percent_female=demo_data.get('percent_female'),
        percent_male=demo_data.get('percent_male'),
        age_range_min=demo_data.get('age_range_min'),
        age_range_max=demo_data.get('age_range_max'),
        age_notes=demo_data.get('age_notes', ''),
        race_distribution=demo_data.get('race_distribution', ''),
        notes=demo_data.get('notes', ''),
    )

    # --- Risk of Bias ---
    rob_data = data.get('risk_of_bias', {})
    rob = RiskOfBiasAssessment.objects.create(
        extraction=extraction,
        framework=rob_data.get('framework', ''),
        overall_rating=rob_data.get('overall_rating', ''),
        notes=rob_data.get('notes', ''),
    )
    for domain_data in rob_data.get('domains', []):
        if domain_data.get('domain_name'):
            RiskOfBiasDomain.objects.create(
                assessment=rob,
                domain_name=domain_data.get('domain_name', ''),
                rating=domain_data.get('rating', ''),
                notes=domain_data.get('notes', ''),
            )

    # --- Assessment Tools ---
    for tool_data in data.get('assessment_tools', []):
        tool_id = tool_data.get('tool_id')
        if not tool_id:
            continue
        try:
            tool_usage = AssessmentToolUsage.objects.create(
                extraction=extraction,
                tool_id=tool_id,
                used_as=tool_data.get('used_as', 'primary'),
                sample_size=tool_data.get('sample_size'),
                age_range_min=tool_data.get('age_range_min'),
                age_range_max=tool_data.get('age_range_max'),
                population_type_id=tool_data.get('population_type_id'),
                sample_descriptor=tool_data.get('sample_descriptor', ''),
                administration_timing=tool_data.get('administration_timing', ''),
                scoring_method=tool_data.get('scoring_method', ''),
                notes=tool_data.get('notes', ''),
            )
            for outcome_data in tool_data.get('outcomes', []):
                domain_id = outcome_data.get('domain_id')
                if not domain_id:
                    continue
                try:
                    OutcomeDomain.objects.create(
                        assessment_tool_usage=tool_usage,
                        domain_id=domain_id,
                        direction=outcome_data.get('direction', ''),
                        outcome_metric=outcome_data.get('outcome_metric', ''),
                        predictor=outcome_data.get('predictor', ''),
                        is_case_control=outcome_data.get('is_case_control', False),
                        effect_size_type=outcome_data.get('effect_size_type', ''),
                        effect_size_value=outcome_data.get('effect_size_value'),
                        confidence_interval=outcome_data.get('confidence_interval', ''),
                        p_value=outcome_data.get('p_value', ''),
                        significance=outcome_data.get('significance', ''),
                        result_description=outcome_data.get('result_description', ''),
                        notes=outcome_data.get('notes', ''),
                    )
                except Exception:
                    continue
        except Exception:
            continue

    # --- Statistical Methods ---
    for method_data in data.get('statistical_methods', []):
        try:
            StatisticalMethod.objects.create(
                extraction=extraction,
                method_category=method_data.get('method_category', ''),
                method_name_id=method_data.get('method_name_id'),
                notes=method_data.get('notes', ''),
            )
        except Exception:
            continue

    # --- Predictors ---
    for predictor_data in data.get('predictors', []):
        try:
            PredictorCovariate.objects.create(
                extraction=extraction,
                category_id=predictor_data.get('category_id'),
                description=predictor_data.get('description', ''),
                notes=predictor_data.get('notes', ''),
            )
        except Exception:
            continue

    return extraction


def run_llm_extraction(publication: Publication) -> ExtractionRecord:
    """
    Run an LLM extraction for a publication.
    Uses PDF text if available, otherwise falls back to abstract.
    Creates an ExtractionRecord with reviewer_type='llm' and
    submits it to the review queue automatically.
    """
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    terms = _get_approved_terms()
    pdf_text = _extract_pdf_text(publication)
    prompt = _build_prompt(publication, terms, pdf_text)

    message = client.messages.create(
        model=getattr(settings, 'ANTHROPIC_MODEL', 'claude-sonnet-4-20250514'),
        max_tokens=4096,
        messages=[
            {'role': 'user', 'content': prompt}
        ],
    )

    raw_text = message.content[0].text.strip()

    # Strip markdown code fences if present
    if raw_text.startswith('```'):
        lines = raw_text.split('\n')
        raw_text = '\n'.join(lines[1:-1])

    data = json.loads(raw_text)
    extraction = _create_extraction_objects(publication, data)

    # Create review record so it appears in the queue
    ExtractionReview.objects.create(
        extraction=extraction,
        submitted_by=publication.submitted_by,
    )

    # Transition workflow if needed
    current_state = get_current_state(publication)
    if current_state in ('unassigned', 'assigned', 'in_progress'):
        transition(
            publication=publication,
            to_state='pending_review',
            actor=None,
            is_system_action=True,
            comment='LLM extraction submitted automatically.',
        )

    return extraction