import uuid as _uuid
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Set,
    Type,
    Union,
)

from sqlalchemy import (
    UUID,
    Boolean,
    Column,
    ColumnElement,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    Time,
    and_,
    inspect,
    not_,
    or_,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.sql.elements import BinaryExpression

from ..errors import FilterError
from ..schemas.pagination import (
    OPERATORS,
    FilterParam,
)
from .types import ModelType

if TYPE_CHECKING:
    from sqlalchemy.sql import Select


class QueryFilter(Generic[ModelType]):
    # Default allowed operators per column type
    DEFAULT_OPERATORS_BY_TYPE = {
        "string": {
            "eq",
            "ne",
            "in",
            "not_in",
            "is_null",
            "is_not_null",
            "like",
            "ilike",
            "startswith",
            "endswith",
            "contains",
        },
        "numeric": {
            "eq",
            "ne",
            "gt",
            "ge",
            "lt",
            "le",
            "in",
            "not_in",
            "is_null",
            "is_not_null",
            "between",
        },
        "datetime": {
            "eq",
            "ne",
            "gt",
            "ge",
            "lt",
            "le",
            "in",
            "not_in",
            "is_null",
            "is_not_null",
            "between",
        },
        "boolean": {"eq", "ne", "in", "not_in", "is_null", "is_not_null"},
        "uuid": {"eq", "ne", "in", "not_in", "is_null", "is_not_null"},
        "default": {"eq", "ne", "in", "not_in", "is_null", "is_not_null"},
    }

    def __init__(
        self,
        model: Type[ModelType],
        allowed_operators: Optional[Dict[str, Set[str]]] = None,
        strict_type_checking: bool = True,
    ):
        self.model = model
        self.strict_type_checking = strict_type_checking
        self.allowed_operators = allowed_operators or self.DEFAULT_OPERATORS_BY_TYPE.copy()

        self._operators: Dict[OPERATORS, Callable[[Column, Any], ColumnElement[bool]]] = {
            "eq": lambda c, v: c == v,
            "ne": lambda c, v: c != v,
            "gt": lambda c, v: c > v,
            "ge": lambda c, v: c >= v,
            "lt": lambda c, v: c < v,
            "le": lambda c, v: c <= v,
            "like": lambda c, v: c.like(v),
            "ilike": lambda c, v: c.ilike(v),
            "in": lambda c, v: c.in_(v),
            "not_in": lambda c, v: ~c.in_(v),
            "is_null": lambda c, v: c.is_(None),
            "is_not_null": lambda c, v: c.is_not(None),
            "contains": lambda c, v: c.contains(v),
            "startswith": lambda c, v: c.startswith(v),
            "endswith": lambda c, v: c.endswith(v),
        }
        self.model_columns = self.get_model_columns(model)

    def _get_column_type_category(self, column: Column) -> str:
        """Determine the category of a column type for operator validation."""
        column_type = column.type

        if isinstance(column_type, (String, Text)):
            return "string"

        if isinstance(column_type, (Integer, Float)) or hasattr(column_type, "python_type"):
            python_type = getattr(column_type, "python_type", None)
            if (
                python_type
                and issubclass(python_type, (int, float, Decimal))
                and not issubclass(python_type, bool)
            ):
                return "numeric"

        if isinstance(column_type, (DateTime, Date, Time)) or (
            hasattr(column_type, "python_type")
            and getattr(column_type, "python_type", None)
            and issubclass(column_type.python_type, (datetime, date, time))
        ):
            return "datetime"

        if isinstance(column_type, Boolean) or (
            hasattr(column_type, "python_type")
            and getattr(column_type, "python_type", None)
            and issubclass(column_type.python_type, bool)
        ):
            return "boolean"

        if isinstance(column_type, (UUID, PostgresUUID)) or (
            hasattr(column_type, "python_type")
            and getattr(column_type, "python_type", None)
            and issubclass(column_type.python_type, _uuid.UUID)
        ):
            return "uuid"

        return "default"

    def _validate_operator_for_field(self, field_name: str, operator: OPERATORS) -> bool:
        model_class = self.model
        if "." in field_name:
            return True

        if operator in ["and", "or", "not"]:
            return True

        try:
            column = getattr(model_class, field_name, None)
            if column is None:
                raise FilterError(f"Field '{field_name}' not found in model {model_class.__name__}")

            column_category = self._get_column_type_category(column)
            allowed_ops = self.allowed_operators.get(
                column_category, self.allowed_operators["default"]
            )

            if operator not in allowed_ops:
                raise FilterError(
                    f"Operator '{operator}' is not allowed for field '{field_name}' "
                    f"of type {column_category}. Allowed operators: {sorted(allowed_ops)}"
                )

            return True
        except Exception as e:
            raise FilterError(str(e))

    def _safe_cast_value(self, column: Column, value: Any) -> Any:
        """Safely cast a value to the column's expected type with comprehensive error handling."""
        if value is None:
            return None

        if isinstance(value, (list, tuple)):
            return [self._safe_cast_value(column, v) for v in value]

        column_type = getattr(column.type, "python_type", None)
        if column_type is None:
            return value

        if isinstance(value, column_type):
            return value

        try:
            # String casting
            if column_type is str:
                return str(value)

            # Boolean casting
            elif column_type is bool:
                if isinstance(value, str):
                    return value.lower() == "true"
                return False

            elif column_type is _uuid.UUID:
                if isinstance(value, str):
                    value = value.strip()
                    if not value:
                        raise ValueError("Empty UUID string")
                    if value.startswith(("uuid:", "urn:uuid:")):
                        value = value.split(":", 1)[1] if ":" in value else value
                    return _uuid.UUID(value)
                return _uuid.UUID(str(value))

            elif column_type in (int, float, Decimal):
                if isinstance(value, str):
                    value = value.strip()
                    if not value:
                        raise ValueError(
                            f"Empty string cannot be converted to {column_type.__name__}"
                        )

                if column_type is int:
                    if isinstance(value, str) and "." in value:
                        return int(float(value))
                    return int(value)
                elif column_type is float:
                    return float(value)
                elif column_type is Decimal:
                    return Decimal(str(value))

            elif column_type in (datetime, date, time):
                if isinstance(value, str):
                    value = value.strip()
                    if not value:
                        raise ValueError(
                            f"Empty string cannot be converted to {column_type.__name__}"
                        )

                    if column_type is datetime:
                        try:
                            if value.endswith("Z"):
                                value = value[:-1] + "+00:00"
                            return datetime.fromisoformat(value)
                        except ValueError:
                            for fmt in [
                                "%Y-%m-%d %H:%M:%S",
                                "%Y-%m-%d %H:%M:%S.%f",
                                "%Y-%m-%dT%H:%M:%S",
                            ]:
                                try:
                                    return datetime.strptime(value, fmt)
                                except ValueError:
                                    continue
                            raise ValueError(f"Could not parse datetime: {value}")

                    elif column_type is date:
                        if isinstance(value, datetime):
                            return value.date()
                        try:
                            return date.fromisoformat(value)
                        except ValueError:
                            try:
                                return datetime.strptime(value, "%Y-%m-%d").date()
                            except ValueError:
                                raise ValueError(f"Could not parse date: {value}")

                    elif column_type is time:
                        try:
                            return time.fromisoformat(value)
                        except ValueError:
                            try:
                                return datetime.strptime(value, "%H:%M:%S").time()
                            except ValueError:
                                raise ValueError(f"Could not parse time: {value}")

                elif column_type is datetime and isinstance(value, date):
                    return datetime.combine(value, time.min)
                elif column_type is date and isinstance(value, datetime):
                    return value.date()
                elif column_type is time and isinstance(value, datetime):
                    return value.time()

            return column_type(value)  # type: ignore

        except (ValueError, TypeError, InvalidOperation) as e:
            if self.strict_type_checking:
                raise FilterError(
                    f"Cannot cast value '{value}' (type: {type(value).__name__}) "
                    f"to column type {column_type.__name__}: {str(e)}"
                )
            else:
                # In non-strict mode, return original value and let SQLAlchemy handle it
                return value
        except Exception as e:
            raise FilterError(f"Unexpected error casting value '{value}': {str(e)}")

    def _validate_filter_value(self, column: Column, operator: OPERATORS, value: Any) -> Any:
        """Validate and cast filter values with comprehensive error handling."""
        if operator in ["is_null", "is_not_null"]:
            if not isinstance(value, bool):
                raise FilterError(
                    f"Operator '{operator}' expects a boolean value (true/false), got {type(value).__name__}"
                )
            return value

        if operator == "between":
            if not isinstance(value, (list, tuple)):
                raise FilterError(
                    f"Operator '{operator}' requires a list/tuple value, got {type(value).__name__}"
                )
            if len(value) != 2:
                raise FilterError(
                    f"Operator '{operator}' requires exactly 2 values, got {len(value)}"
                )
            return [self._safe_cast_value(column, v) for v in value]

        if operator in ["in", "not_in"]:
            if not isinstance(value, (list, tuple)):
                raise FilterError(
                    f"Operator '{operator}' requires a list/tuple value, got {type(value).__name__}"
                )
            if not value:
                raise FilterError(f"Operator '{operator}' requires at least one value")
            return [self._safe_cast_value(column, v) for v in value]

        return self._safe_cast_value(column, value)

    def _build_filter_condition(
        self, filter_param: FilterParam
    ) -> Union[ColumnElement[bool], BinaryExpression, None]:
        """Build a filter condition from a FilterParam, supporting logical operators and nested relationships."""
        try:
            if filter_param.operator in ["and", "or", "not"]:
                return self._build_logical_condition(filter_param)

            if filter_param.field is None:
                raise FilterError(f"Field must be specified for operator '{filter_param.operator}'")

            self._validate_operator_for_field(filter_param.field, filter_param.operator)

            if "." in filter_param.field:
                return self._build_nested_filter_condition(filter_param)

            return self._build_simple_filter_condition(filter_param)

        except FilterError:
            raise
        except Exception as e:
            raise FilterError(f"Error building filter condition: {str(e)}")

    def _build_simple_filter_condition(
        self, filter_param: FilterParam
    ) -> Union[ColumnElement[bool], BinaryExpression, None]:
        """Build a simple filter condition with robust value validation."""
        if filter_param.field is None:
            raise FilterError("Field cannot be None for simple filtering")

        column = getattr(self.model, filter_param.field, None)
        if column is None:
            raise FilterError(
                f"Field '{filter_param.field}' not found in model {self.model.__name__}"
            )

        validated_value = self._validate_filter_value(
            column, filter_param.operator, filter_param.value
        )

        return self._apply_operator_to_column(column, filter_param.operator, validated_value)

    def _build_nested_filter_condition(
        self, filter_param: FilterParam
    ) -> Union[ColumnElement[bool], BinaryExpression, None]:
        """Build nested filter condition with comprehensive support for all relationship types."""
        from sqlalchemy.orm import RelationshipProperty

        if filter_param.field is None:
            raise FilterError("Field cannot be None for nested filtering")

        field_path = filter_param.field.split(".")

        if len(field_path) < 2:
            raise FilterError(f"Invalid nested field path: {filter_param.field}")

        current_model = self.model
        relationship_chain = []

        # Build the relationship chain
        for segment in field_path[:-1]:
            rel_attr = getattr(current_model, segment, None)
            if rel_attr is None:
                raise FilterError(
                    f"Relationship '{segment}' not found in model {current_model.__name__}"
                )

            # Verify it's a relationship
            if not hasattr(rel_attr, "property"):
                raise FilterError(
                    f"'{segment}' is not a valid relationship in model {current_model.__name__}"
                )

            rel_property = rel_attr.property
            if not isinstance(rel_property, RelationshipProperty):
                raise FilterError(
                    f"'{segment}' is not a relationship in model {current_model.__name__}"
                )

            relationship_chain.append(rel_attr)
            current_model = rel_property.mapper.class_

        # Get the target column
        column_name = field_path[-1]
        column_attr = getattr(current_model, column_name, None)
        if column_attr is None:
            raise FilterError(f"Field '{column_name}' not found in model {current_model.__name__}")

        # Validate and build the base condition
        self._validate_operator_for_field(column_name, filter_param.operator)
        validated_value = self._validate_filter_value(
            column_attr, filter_param.operator, filter_param.value
        )
        condition = self._apply_operator_to_column(
            column_attr, filter_param.operator, validated_value
        )

        # Build the nested condition by traversing the relationship chain in reverse
        for rel_attr in reversed(relationship_chain):
            rel_property = rel_attr.property

            # Handle different relationship types
            if rel_property.uselist:
                # Collection-based relationships (one-to-many, many-to-many)
                condition = rel_attr.any(condition)
            else:
                # Scalar relationships (many-to-one, one-to-one)
                condition = rel_attr.has(condition)

        return condition

    def _apply_operator_to_column(
        self, column: Column, operator: OPERATORS, value: Any
    ) -> Union[ColumnElement[bool], BinaryExpression]:
        """Apply operator to column with the validated value."""
        try:
            if operator == "between":
                return column.between(value[0], value[1])
            elif operator in ["in", "not_in"]:
                operator_func = self._operators.get(operator)
                if operator_func is None:
                    raise FilterError(f"Unsupported operator: {operator}")
                return operator_func(column, value)
            elif operator in ["is_null", "is_not_null"]:
                operator_func = self._operators.get(operator)
                if operator_func is None:
                    raise FilterError(f"Unsupported operator: {operator}")
                return operator_func(column, None)
            else:
                operator_func = self._operators.get(operator)
                if operator_func is None:
                    raise FilterError(f"Unsupported operator: {operator}")
                return operator_func(column, value)
        except Exception as e:
            raise FilterError(
                f"Error applying operator '{operator}' to column '{column.name}': {str(e)}"
            )

    def apply_filters(self, query: "Select", filters: List[FilterParam]) -> "Select":
        """Apply filters to the query with support for logical operators and nested relationships."""
        for filter_param in filters:
            condition = self._build_filter_condition(filter_param)
            if condition is not None:
                query = query.where(condition)
        return query

    def _build_logical_condition(
        self, filter_param: FilterParam
    ) -> Union[ColumnElement[bool], BinaryExpression, None]:
        if not isinstance(filter_param.value, list):
            raise FilterError(
                f"Logical operator '{filter_param.operator}' requires a list of FilterParam objects"
            )

        nested_filters = filter_param.value
        if not nested_filters:
            raise FilterError(
                f"Logical operator '{filter_param.operator}' requires at least one nested filter"
            )

        conditions = []
        for nested_filter in nested_filters:
            if not isinstance(nested_filter, FilterParam):
                raise FilterError("Nested filters must be FilterParam objects")
            condition = self._build_filter_condition(nested_filter)
            if condition is not None:
                conditions.append(condition)

        if not conditions:
            return None

        if filter_param.operator == "and":
            result = conditions[0]
            for condition in conditions[1:]:
                result = and_(result, condition)
            return result
        elif filter_param.operator == "or":
            result = conditions[0]
            for condition in conditions[1:]:
                result = or_(result, condition)
            return result
        elif filter_param.operator == "not":
            if len(conditions) != 1:
                raise FilterError("NOT operator requires exactly one nested filter")
            return not_(conditions[0])

        return None

    @staticmethod
    def get_model_columns(model_class) -> Dict[str, Any]:
        mapper = inspect(model_class)
        columns: Dict[str, Any] = {}

        for column in mapper.columns:
            columns[column.name] = {
                "type": column.type,
                "nullable": column.nullable,
                "python_type": column.type.python_type
                if hasattr(column.type, "python_type")
                else str,
            }

        return columns

    def _get_search_fields(self) -> List[str]:
        return [
            name
            for name, info in self.get_model_columns(self.model).items()
            if info.get("type") != "relationship"
            and (
                "str" in str(info.get("python_type", ""))
                or "text" in str(info.get("type", "")).lower()
            )
        ]

    def apply_search(self, query: "Select", search: str, search_fields: List[str]) -> "Select":
        if not search:
            return query

        if not search_fields:
            search_fields = self._get_search_fields()

        if not search_fields:
            return query

        conditions = []
        for field in search_fields:
            column = getattr(self.model, field, None)
            if column is not None and hasattr(column, "ilike"):
                conditions.append(column.ilike(f"%{search}%"))

        if conditions:
            query = query.where(or_(*conditions))

        return query

    def apply_sorting(self, query: "Select", sorting: str) -> "Select":
        order = "desc" if sorting.startswith("-") else "asc"
        field = sorting.lstrip("-")
        column = self.model_columns.get(field)
        if column is None:
            raise FilterError(f"Field '{field}' not found in model {self.model.__name__}")
        if column.get("type") == "relationship":
            raise FilterError(f"Field '{field}' is a relationship and cannot be sorted")
        if order == "desc":
            query = query.order_by(getattr(self.model, field).desc())
        else:
            query = query.order_by(getattr(self.model, field).asc())

        return query
