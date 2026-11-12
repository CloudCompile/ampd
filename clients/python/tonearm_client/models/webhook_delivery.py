from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="WebhookDelivery")


@_attrs_define
class WebhookDelivery:
    """
    Attributes:
        event_id (str):
        event (str):
        hook_id (str):
        url (str):
        attempt (int):
        ok (bool):
        at (float):
        status (int | None | Unset):
        error (None | str | Unset):
        duration_ms (int | None | Unset):
        retry_scheduled (bool | Unset):  Default: False.
    """

    event_id: str
    event: str
    hook_id: str
    url: str
    attempt: int
    ok: bool
    at: float
    status: int | None | Unset = UNSET
    error: None | str | Unset = UNSET
    duration_ms: int | None | Unset = UNSET
    retry_scheduled: bool | Unset = False
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        event_id = self.event_id

        event = self.event

        hook_id = self.hook_id

        url = self.url

        attempt = self.attempt

        ok = self.ok

        at = self.at

        status: int | None | Unset
        if isinstance(self.status, Unset):
            status = UNSET
        else:
            status = self.status

        error: None | str | Unset
        if isinstance(self.error, Unset):
            error = UNSET
        else:
            error = self.error

        duration_ms: int | None | Unset
        if isinstance(self.duration_ms, Unset):
            duration_ms = UNSET
        else:
            duration_ms = self.duration_ms

        retry_scheduled = self.retry_scheduled

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "event_id": event_id,
                "event": event,
                "hook_id": hook_id,
                "url": url,
                "attempt": attempt,
                "ok": ok,
                "at": at,
            }
        )
        if status is not UNSET:
            field_dict["status"] = status
        if error is not UNSET:
            field_dict["error"] = error
        if duration_ms is not UNSET:
            field_dict["duration_ms"] = duration_ms
        if retry_scheduled is not UNSET:
            field_dict["retry_scheduled"] = retry_scheduled

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        event_id = d.pop("event_id")

        event = d.pop("event")

        hook_id = d.pop("hook_id")

        url = d.pop("url")

        attempt = d.pop("attempt")

        ok = d.pop("ok")

        at = d.pop("at")

        def _parse_status(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        status = _parse_status(d.pop("status", UNSET))

        def _parse_error(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        error = _parse_error(d.pop("error", UNSET))

        def _parse_duration_ms(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        duration_ms = _parse_duration_ms(d.pop("duration_ms", UNSET))

        retry_scheduled = d.pop("retry_scheduled", UNSET)

        webhook_delivery = cls(
            event_id=event_id,
            event=event,
            hook_id=hook_id,
            url=url,
            attempt=attempt,
            ok=ok,
            at=at,
            status=status,
            error=error,
            duration_ms=duration_ms,
            retry_scheduled=retry_scheduled,
        )

        webhook_delivery.additional_properties = d
        return webhook_delivery

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
