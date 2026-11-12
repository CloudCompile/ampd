from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="WatchdogState")


@_attrs_define
class WatchdogState:
    """
    Attributes:
        running (bool | None | Unset):
        last_ping_ts (float | None | Unset):
        last_ok (bool | None | Unset):
        consecutive_failures (int | None | Unset):
        recycles (int | None | Unset):
        last_action (None | str | Unset):
    """

    running: bool | None | Unset = UNSET
    last_ping_ts: float | None | Unset = UNSET
    last_ok: bool | None | Unset = UNSET
    consecutive_failures: int | None | Unset = UNSET
    recycles: int | None | Unset = UNSET
    last_action: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        running: bool | None | Unset
        if isinstance(self.running, Unset):
            running = UNSET
        else:
            running = self.running

        last_ping_ts: float | None | Unset
        if isinstance(self.last_ping_ts, Unset):
            last_ping_ts = UNSET
        else:
            last_ping_ts = self.last_ping_ts

        last_ok: bool | None | Unset
        if isinstance(self.last_ok, Unset):
            last_ok = UNSET
        else:
            last_ok = self.last_ok

        consecutive_failures: int | None | Unset
        if isinstance(self.consecutive_failures, Unset):
            consecutive_failures = UNSET
        else:
            consecutive_failures = self.consecutive_failures

        recycles: int | None | Unset
        if isinstance(self.recycles, Unset):
            recycles = UNSET
        else:
            recycles = self.recycles

        last_action: None | str | Unset
        if isinstance(self.last_action, Unset):
            last_action = UNSET
        else:
            last_action = self.last_action

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if running is not UNSET:
            field_dict["running"] = running
        if last_ping_ts is not UNSET:
            field_dict["last_ping_ts"] = last_ping_ts
        if last_ok is not UNSET:
            field_dict["last_ok"] = last_ok
        if consecutive_failures is not UNSET:
            field_dict["consecutive_failures"] = consecutive_failures
        if recycles is not UNSET:
            field_dict["recycles"] = recycles
        if last_action is not UNSET:
            field_dict["last_action"] = last_action

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_running(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        running = _parse_running(d.pop("running", UNSET))

        def _parse_last_ping_ts(data: object) -> float | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(float | None | Unset, data)

        last_ping_ts = _parse_last_ping_ts(d.pop("last_ping_ts", UNSET))

        def _parse_last_ok(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        last_ok = _parse_last_ok(d.pop("last_ok", UNSET))

        def _parse_consecutive_failures(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        consecutive_failures = _parse_consecutive_failures(d.pop("consecutive_failures", UNSET))

        def _parse_recycles(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        recycles = _parse_recycles(d.pop("recycles", UNSET))

        def _parse_last_action(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        last_action = _parse_last_action(d.pop("last_action", UNSET))

        watchdog_state = cls(
            running=running,
            last_ping_ts=last_ping_ts,
            last_ok=last_ok,
            consecutive_failures=consecutive_failures,
            recycles=recycles,
            last_action=last_action,
        )

        watchdog_state.additional_properties = d
        return watchdog_state

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
