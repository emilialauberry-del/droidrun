"""SpanHandler that converts LlamaIndex tags to OpenTelemetry span attributes."""

import inspect
import json
import logging
from typing import Any, Dict, Optional

from llama_index_instrumentation.span_handlers import BaseSpanHandler
from opentelemetry import trace

logger = logging.getLogger("droidrun")


class AttributeSpanHandler(BaseSpanHandler):
    """
    Converts LlamaIndex dispatcher tags to OpenTelemetry span attributes.

    This handler only processes spans from @with_span decorator (detected via
    _with_span_marker tag). Spans from @dispatcher.span are ignored to avoid
    interfering with default LlamaIndex instrumentation behavior.

    Features:
    - Custom tags (list or dict format) → langfuse.trace.tags
    - Level control on success → langfuse.observation.level
    - Error level control → langfuse.observation.level (on exception)
    - IO capture control → langfuse.observation.input/output
    - Auto status messages (errors only, no success message)

    Usage:
        handler = AttributeSpanHandler(capture_io=True)
        dispatcher.add_span_handler(handler)
    """

    def __init__(self, capture_io: bool = True):
        """
        Args:
            capture_io: Default IO capture setting (can be overridden per-span via @with_span)
        """
        self.default_capture_io = capture_io
        # Track active spans to set attributes on them
        self._active_spans: Dict[str, trace.Span] = {}
        # Store per-span configuration
        self._span_config: Dict[str, dict] = {}

    def span_enter(
        self,
        id_: str,
        bound_args: inspect.BoundArguments,
        instance: Optional[Any] = None,
        parent_id: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Called when span starts - check if from @with_span and set attributes."""
        try:
            # Check if this is from @with_span (not @dispatcher.span)
            if not tags or "_with_span_marker" not in tags:
                return  # Skip @dispatcher.span decorated functions

            # Get the current OpenTelemetry span
            current_span = trace.get_current_span()

            # Store reference for span_exit
            self._active_spans[id_] = current_span

            if not current_span or not current_span.is_recording():
                return

            # Copy tags to avoid mutating original
            tags = dict(tags)

            # Extract and remove control flags
            tags.pop("_with_span_marker")
            capture_input = tags.pop("_capture_input", self.default_capture_io)
            capture_output = tags.pop("_capture_output", self.default_capture_io)
            level = tags.pop("_langfuse_level", "DEFAULT")
            error_level = tags.pop("_langfuse_error_level", "ERROR")
            tags_list = tags.pop("_langfuse_tags_list", None)

            # Store config for span_exit and span_drop
            self._span_config[id_] = {
                "capture_output": capture_output,
                "error_level": error_level,
            }

            # Extract span name from id (format: "SpanName-uuid")
            span_name = id_.rsplit("-", 1)[0]

            # Set Langfuse-specific attributes
            current_span.set_attribute("langfuse.observation.name", span_name)
            current_span.set_attribute("langfuse.observation.level", level)

            # Handle tags
            if tags_list:
                # List format: ["tag1", "tag2"]
                current_span.set_attribute("langfuse.trace.tags", json.dumps(tags_list))
            elif tags:
                # Dict format: {"key": "value"} → ["key:value"]
                tag_list = [f"{k}:{v}" for k, v in tags.items()]
                current_span.set_attribute("langfuse.trace.tags", json.dumps(tag_list))
                # Also set individual attributes
                for key, value in tags.items():
                    try:
                        current_span.set_attribute(key, str(value))
                    except Exception as e:
                        logger.debug(f"Failed to set attribute {key}: {e}")

            # Capture input if enabled
            if capture_input:
                try:
                    # Get function arguments (exclude 'self' for methods)
                    args_dict = dict(bound_args.arguments)
                    if instance is not None and "self" in args_dict:
                        args_dict.pop("self")

                    if args_dict:
                        input_str = json.dumps(args_dict, default=str)
                        current_span.set_attribute(
                            "langfuse.observation.input", input_str
                        )
                except Exception as e:
                    logger.debug(f"Failed to capture input: {e}")

        except Exception as e:
            logger.debug(f"Error in AttributeSpanHandler.span_enter: {e}")

    def span_exit(
        self,
        id_: str,
        bound_args: inspect.BoundArguments,
        instance: Optional[Any] = None,
        result: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        """Called when span exits successfully - capture output (no success message)."""
        try:
            config = self._span_config.pop(id_, None)
            current_span = self._active_spans.pop(id_, None)

            # If no config, this wasn't a @with_span span
            if not config or not current_span or not current_span.is_recording():
                return

            # Capture output if enabled
            if (
                config.get("capture_output", self.default_capture_io)
                and result is not None
            ):
                try:
                    output_str = json.dumps(result, default=str)
                    current_span.set_attribute(
                        "langfuse.observation.output", output_str
                    )
                except Exception as e:
                    # Fallback to string representation
                    try:
                        current_span.set_attribute(
                            "langfuse.observation.output", str(result)
                        )
                    except Exception as e2:
                        logger.debug(f"Failed to capture output: {e2}")

            # Note: No status_message on success (removed per requirements)

        except Exception as e:
            logger.debug(f"Error in AttributeSpanHandler.span_exit: {e}")

    def span_drop(
        self,
        id_: str,
        bound_args: inspect.BoundArguments,
        instance: Optional[Any] = None,
        err: Optional[BaseException] = None,
        **kwargs: Any,
    ) -> None:
        """Called when span errors - set error level and status message."""
        try:
            config = self._span_config.pop(id_, None)
            current_span = self._active_spans.pop(id_, None)

            # If no config, this wasn't a @with_span span
            if not config or not current_span or not current_span.is_recording():
                return

            # Use error_level from config (default: ERROR)
            error_level = config.get("error_level", "ERROR")

            # Set error level (not hardcoded ERROR)
            current_span.set_attribute("langfuse.observation.level", error_level)
            if err:
                current_span.set_attribute(
                    "langfuse.observation.status_message", str(err)
                )
                # Also set standard OpenTelemetry error attributes
                current_span.record_exception(err)

        except Exception as e:
            logger.debug(f"Error in AttributeSpanHandler.span_drop: {e}")
