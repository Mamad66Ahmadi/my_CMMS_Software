from django.test import RequestFactory, TestCase

from equipment.views.equipment_views import EquipmentList
from equipment.views.location_tag_views import LocationTagList


class EquipmentListActiveFilterTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def get_context(self, query_string=""):
        request = self.factory.get(f"/equipment/equipment/?{query_string}")
        view = EquipmentList()
        view.setup(request)
        return view.get_context_data()

    def test_active_filters_include_individual_removal_urls(self):
        context = self.get_context(
            "functional_location=P-101&manufacturer=ACME&is_active=false&"
            "sort=model&order=desc&per_page=50&page=3"
        )

        self.assertEqual(
            [(badge["label"], badge["value"]) for badge in context["active_filter_badges"]],
            [
                ("Functional Location", "P-101"),
                ("Manufacturer", "ACME"),
                ("Status", "All equipment"),
            ],
        )
        self.assertNotIn("functional_location=", context["active_filter_badges"][0]["remove_url"])
        self.assertNotRegex(
            context["active_filter_badges"][0]["remove_url"],
            r"[?&]page=",
        )
        self.assertIn("manufacturer=ACME", context["active_filter_badges"][0]["remove_url"])

    def test_clear_filters_preserves_list_preferences(self):
        context = self.get_context(
            "model=TX-4&is_active=false&sort=manufacturer&order=desc&per_page=100&page=2"
        )

        self.assertEqual(
            context["clear_filters_url"],
            "?sort=manufacturer&order=desc&per_page=100",
        )

    def test_default_active_only_setting_is_not_shown_as_a_badge(self):
        context = self.get_context()

        self.assertEqual(context["active_filter_badges"], [])


class LocationTagListActiveFilterTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def get_context(self, query_string=""):
        request = self.factory.get(f"/equipment/location-tags/?{query_string}")
        view = LocationTagList()
        view.setup(request)
        return view.get_context_data()

    def test_active_filters_include_individual_removal_urls(self):
        context = self.get_context(
            "loc_tag=AREA-1&unit=U-100&obj_category=Process&is_active=false&"
            "sort=unit&order=desc&per_page=50&page=4"
        )

        self.assertEqual(
            [(badge["label"], badge["value"]) for badge in context["active_filter_badges"]],
            [
                ("Location Tag", "AREA-1"),
                ("Unit", "U-100"),
                ("Object Category", "Process"),
                ("Status", "All location tags"),
            ],
        )
        first_remove_url = context["active_filter_badges"][0]["remove_url"]
        self.assertNotIn("loc_tag=", first_remove_url)
        self.assertNotRegex(first_remove_url, r"[?&]page=")
        self.assertIn("unit=U-100", first_remove_url)

    def test_clear_filters_preserves_list_preferences(self):
        context = self.get_context(
            "parent=AREA&criticality=High&sort=train&order=desc&per_page=100&page=2"
        )

        self.assertEqual(
            context["clear_filters_url"],
            "?sort=train&order=desc&per_page=100",
        )

    def test_default_active_only_setting_is_not_shown_as_a_badge(self):
        context = self.get_context()

        self.assertEqual(context["active_filter_badges"], [])
