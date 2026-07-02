# work_orders/services/wo_filter_config.py


TEXT_OPERATORS = {
    "eq": "=",
    "neq": "<>",
    "contains": "contains",
    "ncontains": "not contains",
    "startswith": "starts with",
    "endswith": "ends with",
}

NUMERIC_OPERATORS = {
    "eq": "=",
    "neq": "<>",
    "gt": ">",
    "gte": ">=",
    "lt": "<",
    "lte": "<=",
}

DROPDOWN_OPERATORS = {
    "eq": "=",
    "neq": "<>",
}

ACTIVE_FILTER_OPERATOR_LABELS = {
    "eq": "is",
    "neq": "is not",
    "gt": "is greater than",
    "gte": "is greater than or equal to",
    "lt": "is less than",
    "lte": "is less than or equal to",
    "contains": "contains",
    "ncontains": "does not contain",
    "startswith": "starts with",
    "endswith": "ends with",
}

FIELD_CONFIGS = [
    {'name': 'wo_number',          'label': 'WO Number',        'icon': 'hash',         'input_type': 'text',   'placeholder': '2600100, 2600101...',          'operators': 'numeric'},
    {'name': 'reported_at',        'label': 'Reported At',      'icon': 'calendar',     'input_type': 'date',   'placeholder': '',                    'operators': 'numeric'},
    {'name': 'status',             'label': 'Status',           'icon': 'circle-dot',   'input_type': 'select', 'placeholder': 'Default active',      'operators': 'dropdown'},
    {'name': 'priority',           'label': 'Priority',         'icon': 'flag',         'input_type': 'select', 'placeholder': 'All',                 'operators': 'dropdown'},
    {'name': 'symptom',            'label': 'Symptom',          'icon': 'stethoscope',  'input_type': 'select', 'placeholder': 'All',                 'operators': 'dropdown'},
    {'name': 'cause',              'label': 'Cause',            'icon': 'circle-x',     'input_type': 'select', 'placeholder': 'All',                 'operators': 'dropdown'},
    {'name': 'project_code',       'label': 'Project Code',     'icon': 'folder-code',  'input_type': 'select', 'placeholder': 'All',                 'operators': 'dropdown'},
    {'name': 'detection_method',   'label': 'Detection Method', 'icon': 'radar',        'input_type': 'select', 'placeholder': 'All',                 'operators': 'dropdown'},
    {'name': 'work_type',          'label': 'Work Type',        'icon': 'tool',         'input_type': 'select', 'placeholder': 'All',                 'operators': 'dropdown'},
    {'name': 'fault_report',       'label': 'Fault Report',     'icon': 'file-alert',   'input_type': 'text',   'placeholder': '2600200, 2600201...',            'operators': 'numeric'},
    {'name': 'location_tag',       'label': 'Location Tag',     'icon': 'map-pin',      'input_type': 'text',   'placeholder': '103-KM-101, 103-KM-201...',       'operators': 'text'},
    {'name': 'parent_tag',         'label': 'Parent Tag',       'icon': 'sitemap',      'input_type': 'text',   'placeholder': '103-K-101, 103-K-201...',        'operators': 'text'},
    {'name': 'equipment',          'label': 'Equipment Serial', 'icon': 'cpu',          'input_type': 'text',   'placeholder': 'Serial...',           'operators': 'text'},
    {'name': 'reported_by',        'label': 'Reported By',      'icon': 'user',         'input_type': 'text',   'placeholder': 'Username',            'operators': 'text'},
    {'name': 'reported_department','label': 'Reporting Dept.',  'icon': 'building',     'input_type': 'text',   'placeholder': 'CBM, FIX...',         'operators': 'text'},
    {'name': 'directive',          'label': 'Directive',        'icon': 'bolt',         'input_type': 'text',   'placeholder': 'Change, Overhaul...',  'operators': 'text'},
    {'name': 'fault_desc',         'label': 'Fault Description','icon': 'notes',        'input_type': 'text',   'placeholder': 'Leak, vibration...',      'operators': 'text'},
    {'name': 'train',              'label': 'Train',            'icon': 'train',        'input_type': 'number', 'placeholder': '1,2...',                   'operators': 'numeric'},
]
