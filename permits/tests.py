from django.test import SimpleTestCase, TestCase

from equipment.models.equipment_models import TimeStampedModel
from permits.models import (
    PermitPaperSafetyPermit,
    PaperSafetyPermitType,
    PaperSafetyPermitWorkflowStep,
)


class PaperSafetyPermitConfigurationTests(SimpleTestCase):
    def test_configuration_models_use_timestamped_model(self):
        self.assertTrue(issubclass(PaperSafetyPermitType, TimeStampedModel))
        self.assertTrue(issubclass(PaperSafetyPermitWorkflowStep, TimeStampedModel))
        self.assertFalse(issubclass(PermitPaperSafetyPermit, TimeStampedModel))

    def test_operational_statuses_are_hardcoded(self):
        expected = [("ACTIVE", "Active"), ("DEACTIVE", "Deactive")]
        self.assertEqual(list(PermitPaperSafetyPermit.Status.choices), expected)
        self.assertEqual(list(PaperSafetyPermitWorkflowStep.Status.choices), expected)


class PaperSafetyPermitSeedTests(TestCase):
    def test_default_steps_have_required_operational_statuses(self):
        expected = {
            "Pending": "DEACTIVE",
            "Cancelled": "DEACTIVE",
            "Activated": "ACTIVE",
            "Expired": "DEACTIVE",
            "Terminated": "DEACTIVE",
        }
        actual = dict(
            PaperSafetyPermitWorkflowStep.objects.filter(name__in=expected)
            .values_list("name", "status")
        )
        self.assertEqual(actual, expected)
