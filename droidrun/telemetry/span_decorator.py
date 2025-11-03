"""Enhanced span decorator using LlamaIndex dispatcher with custom attribute injection."""

import asyncio
import inspect
import uuid
from contextvars import Context, Token, copy_context
from functools import partial
from typing import Any, Callable, List, Optional, Union

import wrapt
from llama_index_instrumentation.dispatcher import (
    active_instrument_tags,
    DISPATCHER_SPAN_DECORATED_ATTR,
)
from llama_index_instrumentation.events.span import SpanDropEvent
from llama_index_instrumentation.span import active_span_id
import llama_index.core.instrumentation as instrument

dispatcher = instrument.get_dispatcher(__name__)


def with_span(
    name: Optional[str] = None,
    tags: Optional[Union[List[str], dict[str, Any]]] = None,
    level: str = "DEFAULT",
    error_level: str = "ERROR",
    capture_input: bool = True,
    capture_output: bool = True,
) -> Callable:
    """
    Enhanced @dispatcher.span with Langfuse-specific controls.

    Replicates dispatcher.span() behavior exactly, but adds Langfuse observability
    features like custom tags, level control, and IO capture control.

    Args:
        name: Custom span name (default: auto-generated from function/method name)
        tags: List of tag strings ["tag1", "tag2"] OR dict of key-value pairs {"key": "value"}
        level: Langfuse observation level on success - "DEBUG", "DEFAULT", "WARNING", "ERROR" (default: "DEFAULT")
        error_level: Langfuse observation level on exception (default: "ERROR")
        capture_input: Whether to capture function input arguments (default: True)
        capture_output: Whether to capture function return value (default: True)

    Note:
        This decorator is idempotent - applying it multiple times has no effect.
        It properly handles sync functions, async functions, methods, and Future returns.
    """

    def decorator(func: Callable) -> Callable:
        # Idempotency check (same as dispatcher.span)
        try:
            if hasattr(func, DISPATCHER_SPAN_DECORATED_ATTR):
                return func
            setattr(func, DISPATCHER_SPAN_DECORATED_ATTR, True)
        except AttributeError:
            # instance methods can fail with:
            # AttributeError: 'method' object has no attribute '__dispatcher_span_decorated__'
            pass

        # Build control tags with marker to detect @with_span usage
        control_tags = {
            "_with_span_marker": True,
            "_langfuse_level": level,
            "_langfuse_error_level": error_level,
            "_capture_input": capture_input,
            "_capture_output": capture_output,
        }

        # Handle tags parameter
        if isinstance(tags, list):
            # List format: store as special tag
            control_tags["_langfuse_tags_list"] = tags
        elif isinstance(tags, dict):
            # Dict format: merge into control_tags
            control_tags.update(tags)

        # Sync wrapper (exact copy of dispatcher.span wrapper logic)
        @wrapt.decorator
        def wrapper(func: Callable, instance: Any, args: list, kwargs: dict) -> Any:
            bound_args = inspect.signature(func).bind(*args, **kwargs)

            # Generate span ID
            if instance is not None:
                actual_class = type(instance).__name__
                method_name = func.__name__
                id_ = name or f"{actual_class}.{method_name}"
                id_ = f"{id_}-{uuid.uuid4()}"
            else:
                id_ = name or func.__qualname__
                id_ = f"{id_}-{uuid.uuid4()}"

            # Merge active tags with control tags
            active_tags = active_instrument_tags.get()
            merged_tags = {**active_tags, **control_tags}
            result = None

            # Copy the current context (BEFORE try block)
            context = copy_context()

            token = active_span_id.set(id_)
            parent_id = None if token.old_value is Token.MISSING else token.old_value
            dispatcher.span_enter(
                id_=id_,
                bound_args=bound_args,
                instance=instance,
                parent_id=parent_id,
                tags=merged_tags,
            )

            def handle_future_result(
                future: asyncio.Future,
                span_id: str,
                bound_args: inspect.BoundArguments,
                instance: Any,
                context: Context,
            ) -> None:
                try:
                    result = None if future.exception() else future.result()
                    dispatcher.span_exit(
                        id_=span_id,
                        bound_args=bound_args,
                        instance=instance,
                        result=result,
                    )
                    return result
                except BaseException as e:
                    dispatcher.event(SpanDropEvent(span_id=span_id, err_str=str(e)))
                    dispatcher.span_drop(
                        id_=span_id, bound_args=bound_args, instance=instance, err=e
                    )
                    raise
                finally:
                    try:
                        context.run(active_span_id.reset, token)
                    except ValueError as e:
                        # TODO: Since the context is created in a sync context no in async task,
                        # detaching the token raises an ValueError saying "token was created
                        # in a different Context. We should figure out how to handle active spans
                        # correctly, but for now just suppressing the error so it won't be
                        # surfaced to the user.
                        pass

            try:
                result = func(*args, **kwargs)
                if isinstance(result, asyncio.Future):
                    # If the result is a Future, wrap it
                    new_future = asyncio.ensure_future(result)
                    new_future.add_done_callback(
                        partial(
                            handle_future_result,
                            span_id=id_,
                            bound_args=bound_args,
                            instance=instance,
                            context=context,
                        )
                    )
                    return new_future
                else:
                    # For non-Future results, proceed as before
                    dispatcher.span_exit(
                        id_=id_, bound_args=bound_args, instance=instance, result=result
                    )
                    return result
            except BaseException as e:
                dispatcher.event(SpanDropEvent(span_id=id_, err_str=str(e)))
                dispatcher.span_drop(
                    id_=id_, bound_args=bound_args, instance=instance, err=e
                )
                raise
            finally:
                if not isinstance(result, asyncio.Future):
                    active_span_id.reset(token)

        # Async wrapper (exact copy of dispatcher.span async_wrapper logic)
        @wrapt.decorator
        async def async_wrapper(
            func: Callable, instance: Any, args: list, kwargs: dict
        ) -> Any:
            bound_args = inspect.signature(func).bind(*args, **kwargs)

            # Generate span ID
            if instance is not None:
                actual_class = type(instance).__name__
                method_name = func.__name__
                id_ = name or f"{actual_class}.{method_name}"
                id_ = f"{id_}-{uuid.uuid4()}"
            else:
                id_ = name or func.__qualname__
                id_ = f"{id_}-{uuid.uuid4()}"

            # Merge active tags with control tags
            active_tags = active_instrument_tags.get()
            merged_tags = {**active_tags, **control_tags}

            token = active_span_id.set(id_)
            parent_id = None if token.old_value is Token.MISSING else token.old_value
            dispatcher.span_enter(
                id_=id_,
                bound_args=bound_args,
                instance=instance,
                parent_id=parent_id,
                tags=merged_tags,
            )
            try:
                result = await func(*args, **kwargs)
            except BaseException as e:
                dispatcher.event(SpanDropEvent(span_id=id_, err_str=str(e)))
                dispatcher.span_drop(
                    id_=id_, bound_args=bound_args, instance=instance, err=e
                )
                raise
            else:
                dispatcher.span_exit(
                    id_=id_, bound_args=bound_args, instance=instance, result=result
                )
                return result
            finally:
                active_span_id.reset(token)

        if inspect.iscoroutinefunction(func):
            return async_wrapper(func)  # type: ignore
        else:
            return wrapper(func)  # type: ignore

    return decorator
