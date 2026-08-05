# permits/services/condition_service.py

from django.core.exceptions import ValidationError


class WorkflowConditionEvaluator:
    """
    Evaluates PermitWorkflowCondition rows configured for a transition.

    This is deliberately separated from the model because condition
    evaluation is business logic, not persistence logic.
    """

    @classmethod
    def ensure_transition_allowed(cls, *, permit, transition) -> None:
        conditions = transition.conditions.all()

        failed_conditions = []

        for condition in conditions:
            if not cls.evaluate_condition(
                permit=permit,
                condition=condition,
            ):
                failed_conditions.append(
                    condition.description
                    or (
                        f"{condition.operand}.{condition.field_path} "
                        f"{condition.operator} {condition.expected_value}"
                    )
                )

        if failed_conditions:
            raise ValidationError(
                {
                    "transition": (
                        "This transition is blocked because one or more "
                        "workflow conditions were not met: "
                        + "; ".join(failed_conditions)
                    )
                }
            )

    @classmethod
    def evaluate_condition(cls, *, permit, condition) -> bool:
        actual_value = cls._resolve_operand_value(
            permit=permit,
            operand=condition.operand,
            field_path=condition.field_path,
        )

        return cls._compare(
            actual_value=actual_value,
            operator=condition.operator,
            expected_value=condition.expected_value,
        )

    @staticmethod
    def _resolve_operand_value(*, permit, operand, field_path):
        """
        The model's clean() method already limits allowed paths.
        Do not allow arbitrary getattr paths from admin configuration.
        """

        if operand == "PERMIT":
            source = permit

        elif operand == "PERMIT_TYPE":
            source = permit.permit_type

        else:
            raise ValidationError(
                {"operand": f"Unsupported condition operand: {operand}"}
            )

        # `field_path` is restricted by PermitWorkflowCondition.clean().
        value = source
        for attribute in field_path.split("."):
            value = getattr(value, attribute)

        return value

    @staticmethod
    def _compare(*, actual_value, operator, expected_value) -> bool:
        if operator == "IS_TRUE":
            return actual_value is True

        if operator == "IS_FALSE":
            return actual_value is False

        if operator == "IS_NULL":
            return actual_value is None

        if operator == "NOT_NULL":
            return actual_value is not None

        if operator == "EQ":
            return str(actual_value) == expected_value

        if operator == "NE":
            return str(actual_value) != expected_value

        if operator == "CONTAINS":
            return expected_value in str(actual_value)

        if operator == "IN":
            expected_values = {
                value.strip()
                for value in expected_value.split(",")
                if value.strip()
            }
            return str(actual_value) in expected_values

        if operator in {"GT", "GTE", "LT", "LTE"}:
            return WorkflowConditionEvaluator._compare_ordered(
                actual_value=actual_value,
                operator=operator,
                expected_value=expected_value,
            )

        raise ValidationError(
            {"operator": f"Unsupported condition operator: {operator}"}
        )

    @staticmethod
    def _compare_ordered(*, actual_value, operator, expected_value) -> bool:
        """
        In production, improve this by coercing expected_value according to
        the known type of each permitted field.
        """
        try:
            typed_expected_value = type(actual_value)(expected_value)
        except (TypeError, ValueError):
            raise ValidationError(
                {
                    "expected_value": (
                        f"'{expected_value}' cannot be compared to "
                        f"'{actual_value}'."
                    )
                }
            )

        if operator == "GT":
            return actual_value > typed_expected_value
        if operator == "GTE":
            return actual_value >= typed_expected_value
        if operator == "LT":
            return actual_value < typed_expected_value
        if operator == "LTE":
            return actual_value <= typed_expected_value

        return False
