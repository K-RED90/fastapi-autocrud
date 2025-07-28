from enum import Enum

import pytest

from auto_crud.core.crud.decorators import ActionMetadata, action


class TestActionMetadata:
    """Test suite for ActionMetadata class."""

    def test_action_metadata_initialization(self):
        """Test ActionMetadata initialization with default values."""
        metadata = ActionMetadata(method="GET")

        assert metadata.method == "GET"
        assert metadata.detail is False
        assert metadata.url_path is None
        assert metadata.dependencies == []
        assert metadata.response_model is None
        assert metadata.summary is None
        assert metadata.description is None
        assert metadata.tags is None
        assert metadata.deprecated is False
        assert metadata.status_code == 200

    def test_action_metadata_with_custom_values(self):
        """Test ActionMetadata initialization with custom values."""

        def custom_dependency():
            return "test"

        class CustomResponse:
            pass

        metadata = ActionMetadata(
            method="POST",
            detail=True,
            url_path="custom-path",
            dependencies=[custom_dependency],
            response_model=CustomResponse,
            summary="Test summary",
            description="Test description",
            tags=["test", "custom"],
            deprecated=True,
            status_code=201,
        )

        assert metadata.method == "POST"
        assert metadata.detail is True
        assert metadata.url_path == "custom-path"
        assert metadata.dependencies == [custom_dependency]
        assert metadata.response_model == CustomResponse
        assert metadata.summary == "Test summary"
        assert metadata.description == "Test description"
        assert metadata.tags == ["test", "custom"]
        assert metadata.deprecated is True
        assert metadata.status_code == 201

    def test_action_metadata_with_enum_tags(self):
        """Test ActionMetadata with enum tags."""

        class TestTags(Enum):
            TEST = "test"
            CUSTOM = "custom"

        metadata = ActionMetadata(
            method="GET",
            tags=[TestTags.TEST, TestTags.CUSTOM],
        )

        assert metadata.tags == [TestTags.TEST, TestTags.CUSTOM]

    def test_action_metadata_with_kwargs(self):
        """Test ActionMetadata with additional kwargs."""
        metadata = ActionMetadata(
            method="GET",
            custom_field="custom_value",
            another_field=123,
        )

        assert metadata.kwargs["custom_field"] == "custom_value"
        assert metadata.kwargs["another_field"] == 123


class TestActionDecorator:
    """Test suite for action decorator."""

    def test_action_decorator_basic(self):
        """Test basic action decorator usage."""

        @action(method="GET")
        def test_function():
            return "test"

        # Check that the function has the metadata attribute
        assert hasattr(test_function, "_action_metadata")
        metadata = test_function._action_metadata

        assert metadata.method == "GET"
        assert metadata.detail is False
        assert metadata.url_path is None
        assert metadata.dependencies == []
        assert metadata.response_model is None
        assert metadata.summary is None
        assert metadata.description is None
        assert metadata.tags is None
        assert metadata.deprecated is False
        assert metadata.status_code == 200

    def test_action_decorator_with_enum_tags(self):
        """Test action decorator with enum tags."""

        class TestTags(Enum):
            TEST = "test"
            CUSTOM = "custom"

        @action(
            method="GET",
            tags=[TestTags.TEST, TestTags.CUSTOM],
        )
        def test_function():
            return "test"

        metadata = test_function._action_metadata
        assert metadata.tags == [TestTags.TEST, TestTags.CUSTOM]

    def test_action_decorator_status_code_defaults(self):
        """Test action decorator status code defaults."""

        # GET method
        @action(method="GET")
        def get_function():
            pass

        assert get_function._action_metadata.status_code == 200

        # POST method
        @action(method="POST")
        def post_function():
            pass

        assert post_function._action_metadata.status_code == 201

        # PUT method
        @action(method="PUT")
        def put_function():
            pass

        assert put_function._action_metadata.status_code == 200

        # PATCH method
        @action(method="PATCH")
        def patch_function():
            pass

        assert patch_function._action_metadata.status_code == 200

        # DELETE method
        @action(method="DELETE")
        def delete_function():
            pass

        assert delete_function._action_metadata.status_code == 204

    def test_action_decorator_with_custom_status_code(self):
        """Test action decorator with custom status code."""

        @action(method="GET", status_code=202)
        def test_function():
            return "test"

        assert test_function._action_metadata.status_code == 202

    def test_action_decorator_with_none_status_code(self):
        """Test action decorator with None status code (should use default)."""

        @action(method="POST", status_code=None)
        def test_function():
            return "test"

        assert test_function._action_metadata.status_code == 201

    def test_action_decorator_with_none_dependencies(self):
        """Test action decorator with None dependencies."""

        @action(method="GET", dependencies=None)
        def test_function():
            return "test"

        assert test_function._action_metadata.dependencies == []

    def test_action_decorator_with_none_tags(self):
        """Test action decorator with None tags."""

        @action(method="GET", tags=None)
        def test_function():
            return "test"

        assert test_function._action_metadata.tags is None

    def test_action_decorator_function_preservation(self):
        """Test that the decorator preserves the original function."""

        @action(method="GET")
        def test_function():
            return "test"

        # The function should still work as expected
        assert test_function() == "test"

    def test_action_decorator_with_parameters(self):
        """Test action decorator with function that has parameters."""

        @action(method="POST")
        def test_function(param1: str, param2: int = 10):
            return f"{param1}_{param2}"

        # The function should still work with parameters
        assert test_function("test", 5) == "test_5"
        assert test_function("test") == "test_10"

    def test_action_decorator_with_async_function(self):
        """Test action decorator with async function."""

        @action(method="GET")
        async def async_test_function():
            return "async_test"

        # Check that the metadata is set
        assert hasattr(async_test_function, "_action_metadata")
        assert async_test_function._action_metadata.method == "GET"

    def test_action_decorator_multiple_decorators(self):
        """Test action decorator with multiple decorators."""

        def other_decorator(func):
            func.other_attr = "other_value"
            return func

        @other_decorator
        @action(method="GET")
        def test_function():
            return "test"

        # Check that both decorators worked
        assert hasattr(test_function, "_action_metadata")
        assert hasattr(test_function, "other_attr")
        assert test_function._action_metadata.method == "GET"
        assert test_function.other_attr == "other_value"

    def test_action_decorator_with_complex_response_model(self):
        """Test action decorator with complex response model."""
        from pydantic import BaseModel

        class ComplexResponse(BaseModel):
            field1: str
            field2: int
            field3: bool

        @action(
            method="POST",
            response_model=ComplexResponse,
            response_model_by_alias=False,
        )
        def test_function():
            return ComplexResponse(field1="test", field2=123, field3=True)

        metadata = test_function._action_metadata
        assert metadata.response_model == ComplexResponse
        assert metadata.response_model_by_alias is False

    def test_action_decorator_with_dependencies_list(self):
        """Test action decorator with multiple dependencies."""

        def dep1():
            return "dep1"

        def dep2():
            return "dep2"

        @action(
            method="GET",
            dependencies=[dep1, dep2],
        )
        def test_function():
            return "test"

        metadata = test_function._action_metadata
        assert metadata.dependencies == [dep1, dep2]

    def test_action_decorator_with_url_path(self):
        """Test action decorator with custom URL path."""

        @action(
            method="GET",
            url_path="custom-endpoint",
        )
        def test_function():
            return "test"

        metadata = test_function._action_metadata
        assert metadata.url_path == "custom-endpoint"

    def test_action_decorator_with_detail_true(self):
        """Test action decorator with detail=True."""

        @action(
            method="GET",
            detail=True,
        )
        def test_function():
            return "test"

        metadata = test_function._action_metadata
        assert metadata.detail is True

    def test_action_decorator_with_kwargs(self):
        """Test action decorator with additional kwargs."""

        @action(
            method="GET",
            custom_field="custom_value",
            another_field=123,
        )
        def test_function():
            return "test"

        metadata = test_function._action_metadata
        assert metadata.kwargs["custom_field"] == "custom_value"
        assert metadata.kwargs["another_field"] == 123

    def test_action_decorator_function_signature_preservation(self):
        """Test that the decorator preserves function signature."""

        @action(method="GET")
        def test_function(param1: str, param2: int = 10, *, kwarg1: bool = True):
            return f"{param1}_{param2}_{kwarg1}"

        # Check that the function signature is preserved
        import inspect

        sig = inspect.signature(test_function)
        params = list(sig.parameters.keys())

        assert "param1" in params
        assert "param2" in params
        assert "kwarg1" in params


class TestActionDecoratorEdgeCases:
    """Test suite for action decorator edge cases."""

    def test_action_decorator_with_empty_dependencies(self):
        """Test action decorator with empty dependencies list."""

        @action(method="GET", dependencies=[])
        def test_function():
            return "test"

        metadata = test_function._action_metadata
        assert metadata.dependencies == []

    def test_action_decorator_with_empty_tags(self):
        """Test action decorator with empty tags list."""

        @action(method="GET", tags=[])
        def test_function():
            return "test"

        metadata = test_function._action_metadata
        assert metadata.tags == []

    def test_action_decorator_with_empty_url_path(self):
        """Test action decorator with empty URL path."""

        @action(method="GET", url_path="")
        def test_function():
            return "test"

        metadata = test_function._action_metadata
        assert metadata.url_path == ""

    def test_action_decorator_with_none_url_path(self):
        """Test action decorator with None URL path."""

        @action(method="GET", url_path=None)
        def test_function():
            return "test"

        metadata = test_function._action_metadata
        assert metadata.url_path is None

    def test_action_decorator_with_none_response_model(self):
        """Test action decorator with None response model."""

        @action(method="GET", response_model=None)
        def test_function():
            return "test"

        metadata = test_function._action_metadata
        assert metadata.response_model is None

    def test_action_decorator_with_none_summary(self):
        """Test action decorator with None summary."""

        @action(method="GET", summary=None)
        def test_function():
            return "test"

        metadata = test_function._action_metadata
        assert metadata.summary is None

    def test_action_decorator_with_none_description(self):
        """Test action decorator with None description."""

        @action(method="GET", description=None)
        def test_function():
            return "test"

        metadata = test_function._action_metadata
        assert metadata.description is None

    def test_action_decorator_with_false_response_model_by_alias(self):
        """Test action decorator with response_model_by_alias=False."""

        @action(method="GET", response_model_by_alias=False)
        def test_function():
            return "test"

        metadata = test_function._action_metadata
        assert metadata.response_model_by_alias is False

    def test_action_decorator_with_false_deprecated(self):
        """Test action decorator with deprecated=False."""

        @action(method="GET", deprecated=False)
        def test_function():
            return "test"

        metadata = test_function._action_metadata
        assert metadata.deprecated is False

    def test_action_decorator_with_false_detail(self):
        """Test action decorator with detail=False."""

        @action(method="GET", detail=False)
        def test_function():
            return "test"

        metadata = test_function._action_metadata
        assert metadata.detail is False

    def test_action_decorator_with_zero_status_code(self):
        """Test action decorator with status_code=0."""

        @action(method="GET", status_code=0)
        def test_function():
            return "test"

        metadata = test_function._action_metadata
        assert metadata.status_code == 0

    def test_action_decorator_with_negative_status_code(self):
        """Test action decorator with negative status code."""

        @action(method="GET", status_code=-1)
        def test_function():
            return "test"

        metadata = test_function._action_metadata
        assert metadata.status_code == -1

    def test_action_decorator_with_large_status_code(self):
        """Test action decorator with large status code."""

        @action(method="GET", status_code=999)
        def test_function():
            return "test"

        metadata = test_function._action_metadata
        assert metadata.status_code == 999

    def test_action_decorator_with_complex_kwargs(self):
        """Test action decorator with complex kwargs."""
        complex_obj = {"nested": {"value": 123}}

        @action(
            method="GET",
            complex_kwarg=complex_obj,
            list_kwarg=[1, 2, 3],
            tuple_kwarg=(1, 2, 3),
        )
        def test_function():
            return "test"

        metadata = test_function._action_metadata
        assert metadata.kwargs["complex_kwarg"] == complex_obj
        assert metadata.kwargs["list_kwarg"] == [1, 2, 3]
        assert metadata.kwargs["tuple_kwarg"] == (1, 2, 3)

    def test_action_decorator_with_function_as_kwarg(self):
        """Test action decorator with function as kwarg."""

        def kwarg_function():
            return "kwarg_value"

        @action(
            method="GET",
            function_kwarg=kwarg_function,
        )
        def test_function():
            return "test"

        metadata = test_function._action_metadata
        assert metadata.kwargs["function_kwarg"] == kwarg_function

    def test_action_decorator_with_none_kwargs(self):
        """Test action decorator with None as kwarg."""

        @action(
            method="GET",
            none_kwarg=None,
        )
        def test_function():
            return "test"

        metadata = test_function._action_metadata
        assert metadata.kwargs["none_kwarg"] is None

    def test_action_decorator_with_boolean_kwargs(self):
        """Test action decorator with boolean kwargs."""

        @action(
            method="GET",
            true_kwarg=True,
            false_kwarg=False,
        )
        def test_function():
            return "test"

        metadata = test_function._action_metadata
        assert metadata.kwargs["true_kwarg"] is True
        assert metadata.kwargs["false_kwarg"] is False

    def test_action_decorator_with_numeric_kwargs(self):
        """Test action decorator with numeric kwargs."""

        @action(
            method="GET",
            int_kwarg=123,
            float_kwarg=123.456,
            negative_kwarg=-123,
        )
        def test_function():
            return "test"

        metadata = test_function._action_metadata
        assert metadata.kwargs["int_kwarg"] == 123
        assert metadata.kwargs["float_kwarg"] == 123.456
        assert metadata.kwargs["negative_kwarg"] == -123

    def test_action_decorator_with_string_kwargs(self):
        """Test action decorator with string kwargs."""

        @action(
            method="GET",
            empty_string_kwarg="",
            normal_string_kwarg="test",
            special_chars_kwarg="!@#$%^&*()",
        )
        def test_function():
            return "test"

        metadata = test_function._action_metadata
        assert metadata.kwargs["empty_string_kwarg"] == ""
        assert metadata.kwargs["normal_string_kwarg"] == "test"
        assert metadata.kwargs["special_chars_kwarg"] == "!@#$%^&*()"

