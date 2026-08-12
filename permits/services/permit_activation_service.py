# permits/services/permit_activation_service.py

from datetime import datetime, time, timedelta

from django.utils import timezone


class PermitActivationService:

    ACTIVE_DAYS = 7

    @classmethod
    def activate(cls, *, permit, activated_at=None):
        """
        Establish the validity period when a permit becomes Active.

        valid_from and activated_at are the exact activation timestamp.

        valid_to is the end of the seventh calendar day, inclusive.
        """

        activated_at = activated_at or timezone.now()

        last_valid_date = (
            activated_at.date()
            + timedelta(days=cls.ACTIVE_DAYS - 1)
        )

        current_timezone = timezone.get_current_timezone()

        valid_to = timezone.make_aware(
            datetime.combine(
                last_valid_date,
                time.max,
            ),
            current_timezone,
        )

        permit.activated_at = activated_at
        permit.valid_from = activated_at
        permit.valid_to = valid_to

        return permit

    