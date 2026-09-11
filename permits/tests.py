from types import SimpleNamespace
from unittest.mock import Mock

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase

from accounts.models import User
from equipment.models.equipment_models import LocationTag, TimeStampedModel
from permits.models import (
    Permit,
    PermitPaperSafetyPermit,
    PaperSafetyPermitType,
    PaperSafetyPermitWorkflowStep,
    PermitType,
    PermitWorkflow,
    PermitWorkflowStep,
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
        self.assertIn("Step changed from Pending to Cancelled.", transition.remarks)
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
