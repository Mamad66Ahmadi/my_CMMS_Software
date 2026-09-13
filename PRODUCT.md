# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Existing Django application with server-rendered templates, Django models,
forms, views, admin interfaces, and supporting APIs.

## Users

Personnel of a refinery use the software. The product serves refinery
personnel who need to create, review, discover, manage, and control task
permits and their related operational information.

## Product Purpose

The system controls refinery task permits. It supports authenticated,
role-aware permit creation and discovery, permit validity and lifecycle
management, responsible-person assignment, hazard and special-condition
recording, permit qualifications, reporting, and auditable records.

Success means refinery personnel can manage permits reliably, find the correct
permit quickly, keep permit information tied to the right location and work,
and preserve accountability for important actions and approvals.

## Positioning

This is a refinery permit-control system rather than a generic CMMS. Its
primary focus is the controlled lifecycle, traceability, safety conditions,
qualifications, and operational context of refinery task permits. Equipment,
locations, work orders, accounts, and related records support permit control
rather than defining the product's center of gravity.

## Operating Context

The software is used in a refinery operational environment where task permits
must be associated with locations, work orders, departments, responsible
people, hazards, validity periods, and special work conditions. Permit records
may continue previous permits and must remain attributable through their
lifecycle and related approval or review actions.

The application also maintains supporting equipment and location information,
routes selected asset changes through review, and provides authenticated users
with searchable, filterable, sortable, paginated, and exportable records.

## Capabilities and Constraints

- Authenticated access with role-aware permissions is required.
- Permit records support draft and controlled lifecycle states, validity
  periods, locations, work orders, departments, responsible personnel,
  hazards, special conditions, continuations, and audit information.
- PIS qualifications and other account information support permit operations.
- Equipment and location-tag changes use attributable approval workflows.
- Permit, equipment, and location data support filtering, sorting, pagination,
  and CSV export.
- Existing product requirements and implementation are documented in
  `docs/PRD/PRD.md` and the Django application modules.
- The permit transition matrix and some ownership details remain product
  decisions to confirm; the existing PRD identifies these as open issues.
- Inventory, spare parts, procurement, preventive-maintenance scheduling, and
  full permit isolation execution are outside the current product scope unless
  explicitly added later.

## Evidence on Hand

- Current product requirements: `docs/PRD/PRD.md`.
- Permit and safety specifications: `docs/safety permit/`.
- Existing Django applications for `accounts`, `equipment`, `permits`,
  `work_orders`, and `daily_reports`.
- Existing models, forms, views, templates, admin interfaces, tests, and
  migrations in the repository.
- No confirmed brand system, visual direction, testimonials, or external
  customer evidence has been provided. Future work must not fabricate these.

## Product Principles

- Permit control is the product's center of gravity.
- Safety-relevant information must be explicit, attributable, and traceable.
- A permit must stay connected to the correct work, location, people, and
  validity context.
- Access and workflow authority must reflect refinery responsibilities.
- Supporting CMMS data should make permit work faster and more reliable.

