# CMMS Entity Relationship Diagram

This ERD is derived from the current Django model definitions in:

- `accounts/models.py`
- `daily_reports/models.py`
- `equipment/models/*.py`
- `permits/models/*.py`
- `work_orders/models/*.py`

The diagrams focus on application-owned business tables. Django framework tables,
automatically generated `django-simple-history` tables, and commented-out models are
not included.

## Conventions

- `PK` = primary key
- `FK` = foreign key
- `UK` = unique key
- A field ending in `_id` represents Django's database column for a relation.
- `TimeStampedModel` children also contain `created_at`, `created_by_id`,
  `modified_at`, `modified_by_id`, and `is_active`.
- `AuditHistoryModel` children also contain `created_date`, `created_by_id`,
  `modified_date`, `modified_by_id`, and `is_active`.
- Audit-user relationship lines are omitted from the diagrams to keep the core
  business relationships readable.

## System Overview

```mermaid
erDiagram
    DEPARTMENT o|--o{ USER : contains
    USER ||--o{ USER_QUALIFICATION : holds
    QUALIFICATION ||--o{ USER_QUALIFICATION : grants
    USER ||--o{ USER_FILTER_FAVORITE : saves

    OBJECT_CRITICALITY o|--o{ LOCATION_TAG : classifies
    OBJECT_TYPE o|--o{ LOCATION_TAG : types
    OBJECT_CATEGORY o|--o{ LOCATION_TAG : categorizes
    UNIT o|--o{ LOCATION_TAG : groups
    LOCATION_TAG o|--o{ LOCATION_TAG : parent_of
    LOCATION_TAG o|--o{ EQUIPMENT : hosts
    EQUIPMENT ||--o{ EQUIPMENT_DOCUMENT : has

    LOCATION_TAG o|--o{ FAULT_REPORT : identifies
    EQUIPMENT o|--o{ FAULT_REPORT : concerns
    DEPARTMENT ||--o{ FAULT_REPORT : reports
    PRIORITY o|--o{ FAULT_REPORT : prioritizes
    SYMPTOM o|--o{ FAULT_REPORT : describes
    PROJECT_CODE o|--o{ FAULT_REPORT : assigns
    DETECTION_METHOD o|--o{ FAULT_REPORT : detects
    WORK_TYPE o|--o{ FAULT_REPORT : classifies

    FAULT_REPORT o|--o| WORK_ORDER : converts_to
    LOCATION_TAG o|--o{ WORK_ORDER : locates
    EQUIPMENT o|--o{ WORK_ORDER : targets
    WORK_ORDER o|--o{ WORK_ORDER : parent_of
    WORK_ORDER ||--o{ WORK_ORDER_TASK : contains
    DEPARTMENT ||--o{ WORK_ORDER_TASK : requests
    DEPARTMENT ||--o{ WORK_ORDER_TASK : executes
    PERFORMED_ACTION o|--o{ WORK_ORDER_TASK : records
    AWAITING_REASON o|--o{ WORK_ORDER_TASK : delays

    WORK_ORDER o|--o{ PERMIT : supports
    LOCATION_TAG o|--o{ PERMIT : covers
    DEPARTMENT ||--o{ PERMIT : owns
    PERMIT o|--o{ PERMIT : continues
    PERMIT ||--o{ PERMIT_HAZARD_CODE : has
    HAZARD_CODE ||--o{ PERMIT_HAZARD_CODE : classifies

    LOCATION_TAG ||--o{ DAILY_REPORT : appears_in
    LOCATION_TAG o|--o{ DAILY_REPORT : father_tag
    DEPARTMENT ||--o{ DAILY_REPORT : submits

    LOCATION_TAG o|--o{ LOCATION_TAG_CHANGE_REQUEST : target
    EQUIPMENT o|--o{ EQUIPMENT_CHANGE_REQUEST : target
    EQUIPMENT_CHANGE_REQUEST ||--o{ EQUIPMENT_DOCUMENT_CHANGE_REQUEST : uploads
```

## Accounts

```mermaid
erDiagram
    DEPARTMENT {
        string department_code PK
        string name UK
        text description
    }

    USER {
        bigint id PK
        string username UK
        int personnel_number UK
        string first_name
        string last_name
        string department_code FK
        string role
        boolean is_staff
    }

    QUALIFICATION {
        bigint id PK
        string code UK
        string name UK
        text description
    }

    USER_QUALIFICATION {
        bigint id PK
        bigint user_id FK
        bigint qualification_id FK
        date granted_date
        date expiry_date
        text note
        bigint granted_by_id FK
    }

    USER_FILTER_FAVORITE {
        bigint id PK
        bigint user_id FK
        string app_key
        string view_key
        string name
        json filters
        string sort_by
        int per_page
        boolean is_default
    }

    DEPARTMENT o|--o{ USER : department
    USER ||--o{ USER_QUALIFICATION : qualifications
    QUALIFICATION ||--o{ USER_QUALIFICATION : users
    USER o|--o{ USER_QUALIFICATION : granted_by
    USER ||--o{ USER_FILTER_FAVORITE : favorites
```

`USER_QUALIFICATION` is unique on `(user_id, qualification_id)`.
`USER_FILTER_FAVORITE` is unique on `(user_id, app_key, view_key, name)`, with
at most one default favorite per user and view.

## Equipment Registry

```mermaid
erDiagram
    OBJECT_CRITICALITY {
        bigint id PK
        string obj_crt_level UK
        text description
    }

    OBJECT_TYPE {
        bigint id PK
        string obj_type UK
    }

    OBJECT_CATEGORY {
        bigint id PK
        string category_name UK
    }

    UNIT {
        bigint id PK
        string unit_code UK
        string description
    }

    LOCATION_TAG {
        bigint id PK
        string loc_tag UK
        bigint parent_id FK
        string description
        string long_tag
        bigint obj_criticality_id FK
        bigint obj_type_id FK
        bigint obj_category_id FK
        bigint unit_id FK
        int train
        text note
        string mih_level
    }

    EQUIPMENT {
        bigint id PK
        bigint functional_location_id FK
        string serial_number
        text note
        string manufacturer
        string model
    }

    EQUIPMENT_DOCUMENT {
        bigint id PK
        bigint equipment_id FK
        string file_name
        string file
        string description
    }

    OBJECT_CRITICALITY o|--o{ LOCATION_TAG : obj_criticality
    OBJECT_TYPE o|--o{ LOCATION_TAG : obj_type
    OBJECT_CATEGORY o|--o{ LOCATION_TAG : obj_category
    UNIT o|--o{ LOCATION_TAG : unit
    LOCATION_TAG o|--o{ LOCATION_TAG : parent
    LOCATION_TAG o|--o{ EQUIPMENT : functional_location
    EQUIPMENT ||--o{ EQUIPMENT_DOCUMENT : documents
```

## Faults And Work Orders

```mermaid
erDiagram
    WORK_TYPE {
        bigint id PK
        string work_type_code UK
        string work_type_desc
    }

    SYMPTOM {
        bigint id PK
        string symptom_code UK
        string symptom_desc
    }

    CAUSE {
        bigint id PK
        string cause_code UK
        string cause_info
    }

    PRIORITY {
        bigint id PK
        string priority_code UK
        int priority_level
    }

    AWAITING_REASON {
        bigint id PK
        string awaiting_code UK
        string awaiting_desc
    }

    PROJECT_CODE {
        bigint id PK
        string project_code UK
        string project_code_desc
    }

    PERFORMED_ACTION {
        bigint id PK
        string action_code UK
        string action_desc
    }

    DETECTION_METHOD {
        bigint id PK
        string detection_code UK
        string detection_desc
    }

    DOCUMENT_SEQUENCE {
        bigint id PK
        string code
        int year
        int last_number
    }

    FAULT_REPORT {
        bigint id PK
        string report_number UK
        bigint location_tag_id FK
        bigint equipment_id FK
        string directive
        text fault_desc
        bigint priority_id FK
        bigint symptom_id FK
        bigint project_code_id FK
        string parent_work_order_number
        bigint detection_method_id FK
        bigint work_type_id FK
        string executing_department_id FK
        bigint reported_by_id FK
        string reported_department_id FK
        datetime reported_at
        string status
        bigint reviewed_by_id FK
        datetime reviewed_at
        bigint planner_id FK
        datetime planner_reviewed_at
        text review_comment
    }

    WORK_ORDER {
        bigint id PK
        string wo_number UK
        int wo_number_numeric UK
        bigint fault_report_id FK,UK
        bigint location_tag_id FK
        bigint equipment_id FK
        string directive
        text fault_desc
        bigint priority_id FK
        bigint symptom_id FK
        bigint cause_id FK
        text cause_description
        bigint project_code_id FK
        bigint parent_work_order_id FK
        bigint detection_method_id FK
        bigint work_type_id FK
        bigint reported_by_id FK
        string reported_department_id FK
        datetime reported_at
        bigint modified_by_id FK
        datetime modified_at
        string status
    }

    WORK_ORDER_TASK {
        bigint id PK
        bigint work_order_id FK
        int task_number
        boolean is_main_task
        string task_requester_department_id FK
        string task_executing_department_id FK
        string directive
        text description
        string status
        bigint performed_action_id FK
        text work_done_description
        string permit
        bigint planner_id FK
        date planned_start
        date planned_finish
        bigint awaiting_reason_id FK
        text waiting_history
        text remarks
        datetime actual_start
        datetime actual_finish
        bigint work_master_id FK
        bigint work_leader_id FK
        datetime created_at
        bigint created_by_id FK
        datetime modified_at
        bigint modified_by_id FK
        text modified_itam
    }

    LOCATION_TAG o|--o{ FAULT_REPORT : location_tag
    EQUIPMENT o|--o{ FAULT_REPORT : equipment
    PRIORITY o|--o{ FAULT_REPORT : priority
    SYMPTOM o|--o{ FAULT_REPORT : symptom
    PROJECT_CODE o|--o{ FAULT_REPORT : project_code
    DETECTION_METHOD o|--o{ FAULT_REPORT : detection_method
    WORK_TYPE o|--o{ FAULT_REPORT : work_type
    DEPARTMENT ||--o{ FAULT_REPORT : executing_department
    DEPARTMENT ||--o{ FAULT_REPORT : reported_department

    FAULT_REPORT o|--o| WORK_ORDER : fault_report
    LOCATION_TAG o|--o{ WORK_ORDER : location_tag
    EQUIPMENT o|--o{ WORK_ORDER : equipment
    PRIORITY o|--o{ WORK_ORDER : priority
    SYMPTOM o|--o{ WORK_ORDER : symptom
    CAUSE o|--o{ WORK_ORDER : cause
    PROJECT_CODE o|--o{ WORK_ORDER : project_code
    DETECTION_METHOD o|--o{ WORK_ORDER : detection_method
    WORK_TYPE o|--o{ WORK_ORDER : work_type
    DEPARTMENT ||--o{ WORK_ORDER : reported_department
    WORK_ORDER o|--o{ WORK_ORDER : parent_work_order
    WORK_ORDER ||--o{ WORK_ORDER_TASK : tasks

    DEPARTMENT ||--o{ WORK_ORDER_TASK : requester_department
    DEPARTMENT ||--o{ WORK_ORDER_TASK : executing_department
    PERFORMED_ACTION o|--o{ WORK_ORDER_TASK : performed_action
    AWAITING_REASON o|--o{ WORK_ORDER_TASK : awaiting_reason
```

`DOCUMENT_SEQUENCE` is used transactionally to generate fault-report and
work-order numbers, but there is no database foreign key from either document
table to the sequence table. `WORK_ORDER_TASK` is unique on
`(work_order_id, task_number)`.

The `WORK_ORDER_TASK.permit` field is currently plain text. It is **not** a
foreign key to the `PERMIT` table.

## Permits

```mermaid
erDiagram
    HAZARD_CODE {
        bigint id PK
        string code UK
        string name
        text description
        boolean is_active
    }

    PERMIT {
        bigint id PK
        string permit_number UK
        bigint continuation_of_id FK
        bigint location_tag_id FK
        text description
        bigint work_order_id FK
        string department_id FK
        bigint authorized_issuer_id FK
        bigint permit_holder_id FK
        datetime valid_from
        datetime valid_to
        boolean is_excavation
        boolean requires_loto
        boolean is_confined_space
        boolean is_equipment_test
        boolean is_radiography
        boolean is_diving
        string status
        text comment
        datetime created_at
        bigint created_by_id FK
        datetime modified_at
        bigint modified_by_id FK
    }

    PERMIT_HAZARD_CODE {
        bigint id PK
        bigint permit_id FK
        bigint hazardcode_id FK
    }

    PERMIT o|--o{ PERMIT : continuation_of
    LOCATION_TAG o|--o{ PERMIT : location_tag
    WORK_ORDER o|--o{ PERMIT : work_order
    DEPARTMENT ||--o{ PERMIT : department
    USER ||--o{ PERMIT : authorized_issuer
    USER o|--o{ PERMIT : permit_holder
    PERMIT ||--o{ PERMIT_HAZARD_CODE : hazard_links
    HAZARD_CODE ||--o{ PERMIT_HAZARD_CODE : permit_links
```

`PERMIT_HAZARD_CODE` represents Django's automatically created join table for
the `Permit.hazard_codes` many-to-many field.

## Daily Reports

```mermaid
erDiagram
    DAILY_REPORT {
        bigint id PK
        date date
        bigint location_tag_id FK
        bigint father_tag_id FK
        string wo_number
        date actual_start
        text description
        string status
        text employees
        string department_id FK
        datetime created_at
        bigint created_by_id FK
        datetime modified_at
        bigint modified_by_id FK
    }

    LOCATION_TAG ||--o{ DAILY_REPORT : location_tag
    LOCATION_TAG o|--o{ DAILY_REPORT : father_tag
    DEPARTMENT ||--o{ DAILY_REPORT : department
    USER o|--o{ DAILY_REPORT : created_by
    USER o|--o{ DAILY_REPORT : modified_by
```

`DAILY_REPORT.wo_number` is currently plain text and does not enforce a foreign
key to `WORK_ORDER`.

## Equipment Change Requests

```mermaid
erDiagram
    LOCATION_TAG_CHANGE_REQUEST {
        bigint id PK
        string action
        string status
        bigint requested_by_id FK
        datetime requested_at
        bigint reviewed_by_id FK
        datetime reviewed_at
        bigint location_tag_id FK
        json changes
        string loc_tag
        bigint parent_id FK
        string description
        string long_tag
        bigint obj_criticality_id FK
        bigint obj_type_id FK
        bigint obj_category_id FK
        bigint unit_id FK
        int train
        text note
        string mih_level
    }

    EQUIPMENT_CHANGE_REQUEST {
        bigint id PK
        string action
        string status
        bigint requested_by_id FK
        datetime requested_at
        bigint reviewed_by_id FK
        datetime reviewed_at
        bigint equipment_id FK
        bigint functional_location_id FK
        string serial_number
        text note
        string manufacturer
        string model
        json changes
    }

    EQUIPMENT_DOCUMENT_CHANGE_REQUEST {
        bigint id PK
        bigint change_request_id FK
        string file
        string file_name
        string description
    }

    LOCATION_TAG o|--o{ LOCATION_TAG_CHANGE_REQUEST : target
    LOCATION_TAG o|--o{ LOCATION_TAG_CHANGE_REQUEST : proposed_parent
    OBJECT_CRITICALITY o|--o{ LOCATION_TAG_CHANGE_REQUEST : proposed_criticality
    OBJECT_TYPE o|--o{ LOCATION_TAG_CHANGE_REQUEST : proposed_type
    OBJECT_CATEGORY o|--o{ LOCATION_TAG_CHANGE_REQUEST : proposed_category
    UNIT o|--o{ LOCATION_TAG_CHANGE_REQUEST : proposed_unit
    USER ||--o{ LOCATION_TAG_CHANGE_REQUEST : requested_by
    USER o|--o{ LOCATION_TAG_CHANGE_REQUEST : reviewed_by

    EQUIPMENT o|--o{ EQUIPMENT_CHANGE_REQUEST : target
    LOCATION_TAG o|--o{ EQUIPMENT_CHANGE_REQUEST : proposed_location
    USER ||--o{ EQUIPMENT_CHANGE_REQUEST : requested_by
    USER o|--o{ EQUIPMENT_CHANGE_REQUEST : reviewed_by
    EQUIPMENT_CHANGE_REQUEST ||--o{ EQUIPMENT_DOCUMENT_CHANGE_REQUEST : document_requests
```

## Model Notes

- `LocationTag` forms a self-referencing hierarchy through `parent_id`.
- A `FaultReport` can be converted to at most one `WorkOrder`.
- A `WorkOrder` may contain many tasks and may have child work orders.
- A `Permit` may continue an earlier permit and may reference a work order,
  a location tag, or both.
- Equipment and location-tag change requests store proposed values separately
  from the target records and apply them only after approval.
- `maintenance/models.py` and `website/models.py` currently define no persisted
  application models.
