from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from equipment.models.request_equipment_models import (
    EquipmentChangeRequest,
    LocationTagChangeRequest,
)


class UserDashboardViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="dashboard-reviewer",
            password="test-password",
            personnel_number=90001,
            first_name="Dashboard",
            last_name="Reviewer",
            is_staff=True,
        )
        self.client.force_login(self.user)

        LocationTagChangeRequest.objects.bulk_create(
            [
                LocationTagChangeRequest(
                    action=LocationTagChangeRequest.Action.CREATE,
                    status=LocationTagChangeRequest.Status.PENDING,
                    requested_by=self.user,
                    loc_tag=f"TEST-LOC-{index:02d}",
                )
                for index in range(12)
            ]
        )
        EquipmentChangeRequest.objects.bulk_create(
            [
                EquipmentChangeRequest(
                    action=EquipmentChangeRequest.Action.CREATE,
                    status=EquipmentChangeRequest.Status.PENDING,
                    requested_by=self.user,
                )
                for _ in range(12)
            ]
        )

    def test_asset_request_tables_have_independent_pagination(self):
        response = self.client.get(
            reverse("accounts:dashboard"),
            {"location_page": 2, "equipment_page": 2},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["location_tag_requests"].number, 2)
        self.assertEqual(response.context["equipment_requests"].number, 2)
        self.assertEqual(len(response.context["location_tag_requests"]), 2)
        self.assertEqual(len(response.context["equipment_requests"]), 2)
        self.assertEqual(response.context["total_asset_requests"], 24)
        self.assertEqual(
            response.context["location_pagination_params"],
            "equipment_page=2",
        )
        self.assertEqual(
            response.context["equipment_pagination_params"],
            "location_page=2",
        )
