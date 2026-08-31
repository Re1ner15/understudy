import time
import uuid
import logging
from datetime import datetime, timezone
from contextvars import ContextVar
from typing import Optional, Dict, Any, List

logger = logging.getLogger("understudy.tracing")

# Context variables for distributed tracing context propagation
_current_trace_id: ContextVar[Optional[str]] = ContextVar("current_trace_id", default=None)
_current_span_id: ContextVar[Optional[str]] = ContextVar("current_span_id", default=None)
_current_meeting_id: ContextVar[Optional[str]] = ContextVar("current_meeting_id", default=None)


def get_current_trace_id() -> Optional[str]:
    """Returns the active trace ID from the async context."""
    return _current_trace_id.get()


def get_current_span_id() -> Optional[str]:
    """Returns the active span ID from the async context."""
    return _current_span_id.get()


def get_current_meeting_id() -> Optional[str]:
    """Returns the active meeting ID from the async context."""
    return _current_meeting_id.get()


def set_current_meeting_id(meeting_id: Optional[str]):
    """Sets the active meeting ID in the current async context."""
    _current_meeting_id.set(meeting_id)


class Span:
    """OpenTelemetry-compatible span recording execution steps, timing,

    parent-child relationships, and metadata attributes.
    """

    def __init__(
        self,
        name: str,
        meeting_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        **attributes,
    ):
        self.name = name
        self.meeting_id = meeting_id or _current_meeting_id.get()
        self.span_id = f"span-{uuid.uuid4().hex[:12]}"

        # Inherit parent span and trace ID from active context if not explicitly provided
        active_parent = parent_id or _current_span_id.get()
        active_trace = trace_id or _current_trace_id.get()

        if not active_trace:
            active_trace = f"trace-{uuid.uuid4().hex[:16]}"

        self.parent_id = active_parent
        self.trace_id = active_trace
        self.attributes: Dict[str, Any] = dict(attributes)
        self.status: str = "ok"

        self.start_perf: float = 0.0
        self.start_ts: str = ""
        self.end_ts: str = ""
        self.latency_ms: float = 0.0

        self._token_trace = None
        self._token_span = None
        self._token_meeting = None

    def set_attribute(self, key: str, value: Any) -> "Span":
        """Sets a key-value attribute on the span."""
        self.attributes[key] = value
        return self

    def set_attributes(self, **kwargs) -> "Span":
        """Sets multiple key-value attributes on the span."""
        self.attributes.update(kwargs)
        return self

    def set_status(self, status: str, error_message: Optional[str] = None) -> "Span":
        """Sets the span status and optional error message."""
        self.status = status
        if error_message:
            self.attributes["error"] = error_message
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Serializes span to OpenTelemetry-style dictionary."""
        span_dict: Dict[str, Any] = {
            "id": self.span_id,
            "spanId": self.span_id,
            "traceId": self.trace_id,
            "parentId": self.parent_id,
            "name": self.name,
            "meetingId": self.meeting_id,
            "startTs": self.start_ts,
            "endTs": self.end_ts,
            "status": self.status,
            "attributes": self.attributes,
            "latencyMs": self.latency_ms,
            "ts": self.start_ts,  # timestamp alias for sorting & backward-compatibility
        }

        # Mirror top-level compatibility fields if present in attributes
        for key in ("safe", "reasons", "actionId", "actionTitle", "category", "model"):
            if key in self.attributes:
                span_dict[key] = self.attributes[key]

        return span_dict

    def _start(self) -> "Span":
        self.start_perf = time.perf_counter()
        self.start_ts = datetime.now(timezone.utc).isoformat()

        # Push context tokens
        self._token_trace = _current_trace_id.set(self.trace_id)
        self._token_span = _current_span_id.set(self.span_id)
        if self.meeting_id:
            self._token_meeting = _current_meeting_id.set(self.meeting_id)

        return self

    def _finish(self, exc_type=None, exc_val=None, exc_tb=None):
        end_perf = time.perf_counter()
        self.end_ts = datetime.now(timezone.utc).isoformat()
        self.latency_ms = round((end_perf - self.start_perf) * 1000, 2)
        self.attributes["latencyMs"] = self.latency_ms

        if exc_type is not None:
            self.status = "error"
            self.attributes["error"] = str(exc_val)
            self.attributes["errorType"] = exc_type.__name__

        span_data = self.to_dict()

        # Persist to Firestore audit collection if meeting_id is set
        target_meeting_id = self.meeting_id or _current_meeting_id.get()
        if target_meeting_id:
            try:
                from understudy_agent import ledger
                ledger.log_span(target_meeting_id, span_data)
            except Exception as err:
                logger.warning(f"Failed to log span '{self.name}' ({self.span_id}) to Firestore: {err}")

        # Pop context tokens
        if self._token_trace is not None:
            _current_trace_id.reset(self._token_trace)
        if self._token_span is not None:
            _current_span_id.reset(self._token_span)
        if self._token_meeting is not None:
            _current_meeting_id.reset(self._token_meeting)

    def __enter__(self) -> "Span":
        return self._start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._finish(exc_type, exc_val, exc_tb)

    async def __aenter__(self) -> "Span":
        return self._start()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._finish(exc_type, exc_val, exc_tb)


def span(
    name: str,
    meeting_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    parent_id: Optional[str] = None,
    **attrs,
) -> Span:
    """Creates a lightweight OpenTelemetry-style span context manager.
    
    Can be used with either `with span(...):` or `async with span(...):`.
    """
    return Span(
        name=name,
        meeting_id=meeting_id,
        trace_id=trace_id,
        parent_id=parent_id,
        **attrs,
    )
