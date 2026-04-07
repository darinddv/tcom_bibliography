from contributor.views.account import (
    work,
    profile,
    register,
    logout_view,
)

from contributor.views.publications import (
    publication_list,
    publication_detail,
    assign_to_me,
    unassign_me,
    import_doi,
    upload_pdf,
    delete_pdf,
    extraction_detail,
    run_llm_extraction_view,
    request_deletion_view,
    cancel_deletion_view,
)

from contributor.views.extraction import (
    extraction_form,
    save_extraction,
    add_rob_domain,
    delete_rob_domain,
    tools_section,
    add_tool_usage,
    delete_tool_usage,
    add_outcome_domain,
    delete_outcome_domain,
    add_statistical_method,
    delete_statistical_method,
    add_predictor,
    delete_predictor,
    submit_extraction_view,
)

from contributor.views.review import (
    review_queue,
    review_detail,
)

from contributor.views.admin_actions import (
    deletion_queue,
    resolve_deletion_view,
)

from contributor.views.bibliography import (
    bibliography,
    bibliography_detail,
)

from contributor.views.dashboard import (
    dashboard,
)

from contributor.views.landing import (
    landing,
)