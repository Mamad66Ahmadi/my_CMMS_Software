from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from accounts.models import User
from equipment.models.equipment_models import LocationTag, TimeStampedModel
from permits.models import (
    Permit,
    PermitPaperSafetyPermit,
    PermitWorkShift,
    PaperSafetyPermitType,
    PaperSafetyPermitWorkflowStep,
    PermitType,
    PermitWorkflow,
    PermitWorkflowStep,
    Shift,
)
from permits.services.paper_safety_permit_service import (
    PaperSafetyPermitReviewService,
)
from permits.services.work_shift_service import (
    PermitWorkShiftError,
    PermitWorkShiftService,
)


class PaperSafetyPermitConfigurationTests(SimpleTestCase):
    def test_configuration_models_use_timestamped_model(self):
        self.assertTrue(issubclass(PaperSafetyPermitType, TimeStampedModel))
        self.assertTrue(issubclass(PaperSafetyPermitWorkflowStep, TimeStampedModel))
        self.assertFalse(issubclass(PermitPaperSafetyPermit, TimeStampedModel))

    def test_workflow_step_separates_state_blocking_and_configuration(self):
        field_names = [
            field.name for field in PaperSafetyPermitWorkflowStep._meta.fields
        ]
        self.assertNotIn("status", field_names)
        self.assertIn("blocks_main_permit", field_names)
        self.assertIn("is_active", field_names)

    def test_permit_state_and_blocking_are_derived_from_current_step(self):
        step = PaperSafetyPermitWorkflowStep(
            name="Activated",
            blocks_main_permit=False,
        )
        permit_safety = PermitPaperSafetyPermit(current_step=step)

        self.assertEqual(permit_safety.status, "Activated")
        self.assertEqual(permit_safety.get_status_display(), "Activated")
        self.assertFalse(permit_safety.blocks_main_permit)

    def test_inactive_workflow_step_cannot_be_assigned(self):
        current_step = PaperSafetyPermitWorkflowStep(
            id=1,
            name="Pending",
            blocks_main_permit=True,
        )
        inactive_step = PaperSafetyPermitWorkflowStep(
            id=2,
            name="Cancelled",
            blocks_main_permit=False,
            is_active=False,
        )
        permit_safety = PermitPaperSafetyPermit(current_step=current_step)
        actor = SimpleNamespace(is_authenticated=True)

        with self.assertRaisesMessage(
            ValidationError,
            "An inactive safety-permit workflow step cannot be assigned.",
        ):
            permit_safety.change_step(step=inactive_step, changed_by=actor)

    def test_activated_step_requires_a_safety_permit_number(self):
        activated_step = PaperSafetyPermitWorkflowStep(
            id=1,
            name="Activated",
            blocks_main_permit=False,
        )
        permit_safety = PermitPaperSafetyPermit(current_step=activated_step)

        with self.assertRaisesMessage(
            ValidationError,
            "A paper safety permit number is required before activation.",
        ):
            permit_safety.clean()

    def test_main_permit_readiness_uses_blocking_steps_for_multiple_permits(self):
        related_manager = Mock()
        blocking_queryset = Mock()
        related_manager.filter.return_value = blocking_queryset
        permit = SimpleNamespace(paper_safety_permits=related_manager)

        blocking_queryset.exists.return_value = True
        self.assertFalse(
            Permit.safety_permits_ready_for_activation.fget(permit)
        )

        blocking_queryset.exists.return_value = False
        self.assertTrue(
            Permit.safety_permits_ready_for_activation.fget(permit)
        )
        related_manager.filter.assert_called_with(
            current_step__blocks_main_permit=True
        )


class PaperSafetyPermitSeedTests(TestCase):
    def test_default_steps_have_required_blocking_behaviour(self):
        expected = {
            "Pending": True,
            "Cancelled": False,
            "Activated": False,
            "Expired": True,
            # The previous readiness rule treated Terminated as blocking.
            "Terminated": True,
        }
        actual = dict(
            PaperSafetyPermitWorkflowStep.objects.filter(name__in=expected)
            .values_list("name", "blocks_main_permit")
        )
        self.assertEqual(actual, expected)


class PaperSafetyPermitWorkflowTests(TestCase):
    def setUp(self):
        self.actor = User.objects.create_user(
            username="paper-reviewer",
            personnel_number=90001,
            first_name="Paper",
            last_name="Reviewer",
        )
        workflow = PermitWorkflow.objects.create(name="Paper safety test")
        start_step = PermitWorkflowStep.objects.create(
            workflow=workflow,
            step_number=1,
            title="Draft",
            state=PermitWorkflowStep.State.DRAFT,
            is_start=True,
        )
        permit_type = PermitType.objects.create(
            code="PAPER_TEST",
            name="Paper safety test",
            active_workflow=workflow,
        )
        location = LocationTag.objects.create(loc_tag="PAPER-TEST-LOCATION")
        self.permit = Permit.objects.create(
            permit_number="PAPER-TEST-001",
            permit_type=permit_type,
            workflow=workflow,
            current_step=start_step,
            location_tag=location,
            scope_of_work="Test paper safety workflow",
            created_by=self.actor,
        )
        self.safety_type = PaperSafetyPermitType.objects.create(
            code="PAPER_TEST_TYPE",
            name="Paper safety test type",
        )

    def create_safety_permit(self, number=""):
        return PermitPaperSafetyPermit.objects.create(
            permit=self.permit,
            safety_type=self.safety_type,
            safety_permit_number=number,
            created_by=self.actor,
        )

    def test_transitions_audit_and_multiple_permit_readiness(self):
        cancelled_permit = self.create_safety_permit()
        initial_event = cancelled_permit.status_history.get()
        self.assertEqual(initial_event.from_status, "")
        self.assertEqual(initial_event.to_status, "Pending")
        self.assertEqual(initial_event.remarks, "")
        self.assertFalse(self.permit.safety_permits_ready_for_activation)

        cancelled_permit.change_step(
            step=PaperSafetyPermitWorkflowStep.objects.get(name="Cancelled"),
            changed_by=self.actor,
            remarks="Not required for this job.",
        )
        cancelled_permit.refresh_from_db()
        transition = cancelled_permit.status_history.first()
        self.assertEqual(cancelled_permit.status, "Cancelled")
        self.assertFalse(cancelled_permit.blocks_main_permit)
        self.assertEqual(transition.from_status, "Pending")
        self.assertEqual(transition.to_status, "Cancelled")
        self.assertEqual(transition.remarks, "Not required for this job.")
        self.assertTrue(self.permit.safety_permits_ready_for_activation)

        activated_permit = self.create_safety_permit("SAFETY-002")
        self.assertFalse(self.permit.safety_permits_ready_for_activation)
        activated_permit.change_step(
            step=PaperSafetyPermitWorkflowStep.objects.get(name="Activated"),
            changed_by=self.actor,
        )

        cancelled_permit.refresh_from_db()
        activated_permit.refresh_from_db()
        self.assertEqual(cancelled_permit.status, "Cancelled")
        self.assertEqual(activated_permit.status, "Activated")
        self.assertTrue(self.permit.safety_permits_ready_for_activation)

    def test_generic_step_action_requires_comment_only_for_cancelled(self):
        self.actor.is_superuser = True
        self.actor.save(update_fields=["is_superuser"])
        paper_safety_permit = self.create_safety_permit()
        cancelled = PaperSafetyPermitWorkflowStep.objects.get(name="Cancelled")
        expired = PaperSafetyPermitWorkflowStep.objects.get(name="Expired")

        with self.assertRaisesMessage(
            ValidationError,
            "A comment is required when cancelling a paper safety permit.",
        ):
            PaperSafetyPermitReviewService.assign_step(
                paper_safety_permit_id=paper_safety_permit.pk,
                actor=self.actor,
                step_id=cancelled.pk,
            )

        PaperSafetyPermitReviewService.assign_step(
            paper_safety_permit_id=paper_safety_permit.pk,
            actor=self.actor,
            step_id=expired.pk,
        )
        paper_safety_permit.refresh_from_db()
        self.assertEqual(paper_safety_permit.status, "Expired")
        self.assertEqual(paper_safety_permit.status_history.first().remarks, "")

    def test_generic_activated_action_accepts_permit_number(self):
        self.actor.is_superuser = True
        self.actor.save(update_fields=["is_superuser"])
        paper_safety_permit = self.create_safety_permit()
        activated = PaperSafetyPermitWorkflowStep.objects.get(name="Activated")

        PaperSafetyPermitReviewService.assign_step(
            paper_safety_permit_id=paper_safety_permit.pk,
            actor=self.actor,
            step_id=activated.pk,
            safety_permit_number="ACTION-001",
        )
        paper_safety_permit.refresh_from_db()
        self.assertEqual(paper_safety_permit.status, "Activated")
        self.assertEqual(paper_safety_permit.safety_permit_number, "ACTION-001")

    def test_authorized_user_can_add_safety_permit_from_detail_panel(self):
        self.actor.is_superuser = True
        self.actor.save(update_fields=["is_superuser"])
        self.client.force_login(self.actor)

        response = self.client.post(
            reverse(
                "permits:paper_safety_permit_add",
                kwargs={"permit_number": self.permit.permit_number},
            ),
            {
                "safety_type": self.safety_type.pk,
                "safety_permit_number": "DETAIL-001",
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        added = self.permit.paper_safety_permits.get(
            safety_permit_number="DETAIL-001"
        )
        self.assertEqual(added.status, "Pending")
        self.assertEqual(added.status_history.get().remarks, "")

    def test_work_shift_creation_requires_all_safety_permits_non_blocking(self):
        cancelled_permit = self.create_safety_permit()
        cancelled_permit.change_step(
            step=PaperSafetyPermitWorkflowStep.objects.get(name="Cancelled"),
            changed_by=self.actor,
            remarks="Not required.",
        )
        pending_permit = self.create_safety_permit()

        with self.assertRaisesMessage(
            PermitWorkShiftError,
            "You should first get the approval of your safety permits.",
        ):
            PermitWorkShiftService._ensure_safety_permits_do_not_block_work_shift(
                self.permit
            )

        pending_permit.safety_permit_number = "SHIFT-SAFETY-001"
        pending_permit.change_step(
            step=PaperSafetyPermitWorkflowStep.objects.get(name="Activated"),
            changed_by=self.actor,
        )

        PermitWorkShiftService._ensure_safety_permits_do_not_block_work_shift(
            self.permit
        )


class WorkShiftListViewTests(TestCase):
    def setUp(self):
        self.actor = User.objects.create_user(
            username="work-shift-list-user",
            personnel_number=90002,
        )
        workflow = PermitWorkflow.objects.create(name="Work shift list test")
        permit_type = PermitType.objects.create(
            code="SHIFT_LIST_TEST",
            name="Work shift list test",
            active_workflow=workflow,
        )
        permits = [
            Permit(
                permit_number=f"SHIFT-LIST-{index:03d}",
                permit_type=permit_type,
                workflow=workflow,
                scope_of_work="Pagination test",
                created_by=self.actor,
            )
            for index in range(52)
        ]
        Permit.objects.bulk_create(permits)
        PermitWorkShift.objects.bulk_create(
            [
                PermitWorkShift(
                    permit=permit,
                    date=date(2026, 9, 17),
                    shift=Shift.SHIFT_1 if index < 26 else Shift.SHIFT_2,
                    created_by=self.actor,
                )
                for index, permit in enumerate(permits)
            ]
        )
        self.client.force_login(self.actor)

    def test_each_shift_uses_its_own_paginator_and_query_parameter(self):
        response = self.client.get(
            reverse("permits:work_shift_list"),
            {
                "date": "2026-09-17",
                "shift_1_page": "2",
                "shift_2_page": "2",
                "tab": "shift-2",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["shift_1_work_shifts"].number, 2)
        self.assertEqual(response.context["shift_2_work_shifts"].number, 2)
        self.assertEqual(len(response.context["shift_1_work_shifts"]), 1)
        self.assertEqual(len(response.context["shift_2_work_shifts"]), 1)
        self.assertEqual(response.context["active_work_shift_tab"], "shift-2")

        shift_1_query = response.context["shift_1_query_params"]
        shift_2_query = response.context["shift_2_query_params"]
        self.assertNotIn("shift_1_page=", shift_1_query)
        self.assertIn("shift_2_page=2", shift_1_query)
        self.assertIn("tab=shift-1", shift_1_query)
        self.assertNotIn("shift_2_page=", shift_2_query)
        self.assertIn("shift_1_page=2", shift_2_query)
        self.assertIn("tab=shift-2", shift_2_query)
