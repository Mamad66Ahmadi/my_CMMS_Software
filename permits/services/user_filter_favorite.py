# permits/services/user_filter_favorite.py

FAVORITE_APP_KEY = "permits"
FAVORITE_VIEW_KEY = "permit_list"


# These keys must stay aligned with:
# - get_request_filters()
# - get_post_filters()
# - build_query_string()
# - has_manual_filters()
# - saved favorite JSON payloads
FILTER_KEYS = [
    # Quick search
    "q",

    # Identification
    "permit_number",
    "continuation_of",
    "permit_type",

    # Workflow
    "current_step",
    "workflow",
    "is_terminal",

    # Location / work order
    "location_tag",
    "parent_tag",
    "unit",
    "train",
    "work_order",

    # Department / personnel
    "department",
    "work_supervisor",
    "designated_area_authority",
    "designated_area_supervisor",

    # Work details
    "scope_of_work",
    "remarks",
    "hazard_code",
    "precaution_code",

    # Tools / materials
    "electrical_tools",
    "mechanical_tools",
    "hazardous_materials",
    "vehicle_required",

    # Equipment preparation
    "mechanical_isolation",
    "equipment_depressurized",
    "equipment_drained",
    "equipment_purged",
    "process_isolation",
    "area_authority_present_required",
    "fire_watch_present_required",

    # Validity
    "valid_from_date",
    "valid_to_date",
    "is_currently_valid",
    "has_expired",

    # Workflow lifecycle timestamps
    "activated",
    "suspended",
    "completed",
    "closed",

    # Audit
    "created_from",
    "created_to",
    "modified_from",
    "modified_to",
    "created_by",
    "modified_by",
]


PER_PAGE_CHOICES = [10, 25, 50, 100]
DEFAULT_SORT = "-created_at"
DEFAULT_PER_PAGE = 25
