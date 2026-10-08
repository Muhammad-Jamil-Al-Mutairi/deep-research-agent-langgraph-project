"""Tracing stub - GIVEN by the SDAIA starter notebook (section 2), moved here verbatim.

A small stand-in for Langfuse's @observe decorator. Swap to real Langfuse later by
changing only the import, e.g. ``from langfuse import observe``.

HERMES additions are below the ``# ---- HERMES extensions`` marker: a mission-level
usage collector so tokens and real OpenRouter cost can be totalled per mission.
"""

import asyncio
import functools
import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class Span:
    id: str
    name: str
    start_time: float
    level: int
    type: str = 'span'
    parent: Optional['Span'] = None
    children: List['Span'] = field(default_factory=list)
    end_time: Optional[float] = None
    input: Any = None
    output: Any = None
    metadata: dict = field(default_factory=dict)
    usage: dict = field(default_factory=dict)
    model: Optional[str] = None


_current_span: ContextVar[Optional[Span]] = ContextVar('current_span', default=None)


def print_tree(span: 'Span'):
    """Print one span and all of its children, indented by depth."""
    duration = (span.end_time - span.start_time) * 1000
    indent = '  ' * span.level
    prefix, suffix = ('=== TRACE: ', ' ===') if span.level == 0 else ('|-- ', '')
    meta_parts = []
    if span.model:
        meta_parts.append(f'model={span.model}')
    if span.usage.get('total_tokens'):
        meta_parts.append(f"tokens={span.usage['total_tokens']}")
    if 'cost_usd' in span.metadata:
        meta_parts.append(f"${span.metadata['cost_usd']:.4f}")
    meta_str = f" [{', '.join(meta_parts)}]" if meta_parts else ''
    type_str = f" [{span.type}]" if span.type != 'span' else ''
    print(f'{indent}{prefix}{span.name}{type_str}{suffix} ({duration:.2f}ms){meta_str}')
    for child in span.children:
        print_tree(child)


def _make_span(span_name: str, span_type: str, args, kwargs) -> 'Span':
    parent = _current_span.get()
    level = parent.level + 1 if parent else 0
    span = Span(id=str(uuid.uuid4())[:8], name=span_name, type=span_type,
                start_time=time.time(), level=level, parent=parent,
                input={'args': args, 'kwargs': kwargs})
    if parent:
        parent.children.append(span)
    return span


def _finish_span(span: 'Span'):
    span.end_time = time.time()
    if span.level == 0:
        print('\n' + '-' * 60)
        print_tree(span)
        print('-' * 60 + '\n')


def observe(name=None, as_type=None):
    """Decorator that records a span around a sync or async function."""
    def decorator(func):
        span_name = name if isinstance(name, str) else func.__name__
        span_type = as_type or 'span'

        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                span = _make_span(span_name, span_type, args, kwargs)
                token = _current_span.set(span)
                try:
                    result = await func(*args, **kwargs)
                    if span.output is None:
                        span.output = result
                    return result
                except Exception as e:
                    span.output = f'Error: {e}'
                    raise
                finally:
                    _finish_span(span)
                    _current_span.reset(token)
        else:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                span = _make_span(span_name, span_type, args, kwargs)
                token = _current_span.set(span)
                try:
                    result = func(*args, **kwargs)
                    if span.output is None:
                        span.output = result
                    return result
                except Exception as e:
                    span.output = f'Error: {e}'
                    raise
                finally:
                    _finish_span(span)
                    _current_span.reset(token)

        return wrapper

    # Support both @observe and @observe(name='foo', as_type='bar')
    if callable(name):
        func, name = name, None
        return decorator(func)
    return decorator


class LangfuseContext:
    """Attach usage/model/cost data to the span currently being recorded."""

    def update_current_observation(self, **kwargs):
        span = _current_span.get()
        if not span:
            return
        if isinstance(kwargs.get('usage'), dict):
            span.usage.update(kwargs['usage'])
        if 'model' in kwargs:
            span.model = kwargs['model']
        if isinstance(kwargs.get('metadata'), dict):
            span.metadata.update(kwargs['metadata'])


langfuse_context = LangfuseContext()


# ---- HERMES extensions ------------------------------------------------------


def current_span() -> Optional[Span]:
    """The span currently being recorded (None outside any @observe scope)."""
    return _current_span.get()


def span_totals(span: Span) -> dict:
    """Sum tokens and real OpenRouter cost over a span and all its descendants."""
    tokens = span.usage.get('total_tokens', 0) or 0
    cost = span.metadata.get('cost_usd', 0.0) or 0.0
    agent_runs = 1 if span.type == 'agent' else 0
    for child in span.children:
        sub = span_totals(child)
        tokens += sub['total_tokens']
        cost += sub['cost_usd']
        agent_runs += sub['agent_runs']
    return {'total_tokens': tokens, 'cost_usd': round(cost, 6), 'agent_runs': agent_runs}
