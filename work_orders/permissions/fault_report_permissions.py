from work_orders.models import FaultReportStatus


class FaultReportPermissions:

    @staticmethod
    def is_method_or_staff(user):
        return user.is_staff or (
            user.department and user.department.name == "Method"
        )


    @staticmethod
    def is_supervisor(user, fault):
        return (
            getattr(user, "role", None) == "supervisor"
            and user.department == fault.reported_department
        )

    @staticmethod
    def is_requester(user, fault):
        return user == fault.reported_by


    # --------------------------------
    # VIEW PERMISSIONS
    # --------------------------------

    @classmethod
    def can_review(cls, user, fault):
        if cls.is_method_or_staff(user):
            return fault.status != FaultReportStatus.CONVERTED

        if cls.is_supervisor(user, fault):
            return fault.status == FaultReportStatus.SUBMITTED

        if cls.is_requester(user, fault):
            return fault.status == FaultReportStatus.SUBMITTED

        return False


    @classmethod
    def can_convert(cls, user, fault):
        if fault.status != FaultReportStatus.APPROVED:
            return False

        if cls.is_method_or_staff(user):
            return True

        if cls.is_supervisor(user, fault):
            return True

        return False


    # --------------------------------
    # ACTION PERMISSIONS
    # --------------------------------

    @classmethod
    def can_approve(cls, user, fault):
        return (
            cls.is_method_or_staff(user)
            or cls.is_supervisor(user, fault)
        )

    @classmethod
    def can_reject(cls, user, fault):
        return (
            cls.is_method_or_staff(user)
            or cls.is_supervisor(user, fault)
            or cls.is_requester(user, fault)
        )

    @classmethod
    def can_resubmit(cls, user, fault):
        return (
            fault.status == FaultReportStatus.REJECTED
            and (cls.is_method_or_staff(user))
        )

    @classmethod
    def can_convert_action(cls, user, fault):
        return (
            fault.status == FaultReportStatus.APPROVED
            and cls.is_method_or_staff(user)
        )