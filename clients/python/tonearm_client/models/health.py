from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.session_state import SessionState
    from ..models.watchdog_state import WatchdogState


T = TypeVar("T", bound="Health")


@_attrs_define
class Health:
    """
    Attributes:
        status (str):
        browser (None | str | Unset):
        watchdog (None | Unset | WatchdogState):
        session (None | SessionState | Unset):
        detail (None | str | Unset):
    """

    status: str
    browser: None | str | Unset = UNSET
    watchdog: None | Unset | WatchdogState = UNSET
    session: None | SessionState | Unset = UNSET
    detail: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.session_state import SessionState  # noqa: PLC0415
        from ..models.watchdog_state import WatchdogState  # noqa: PLC0415

        status = self.status

        browser: None | str | Unset
        if isinstance(self.browser, Unset):
            browser = UNSET
        else:
            browser = self.browser

        watchdog: dict[str, Any] | None | Unset
        if isinstance(self.watchdog, Unset):
            watchdog = UNSET
        elif isinstance(self.watchdog, WatchdogState):
            watchdog = self.watchdog.to_dict()
        else:
            watchdog = self.watchdog

        session: dict[str, Any] | None | Unset
        if isinstance(self.session, Unset):
            session = UNSET
        elif isinstance(self.session, SessionState):
            session = self.session.to_dict()
        else:
            session = self.session

        detail: None | str | Unset
        if isinstance(self.detail, Unset):
            detail = UNSET
        else:
            detail = self.detail

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "status": status,
            }
        )
        if browser is not UNSET:
            field_dict["browser"] = browser
        if watchdog is not UNSET:
            field_dict["watchdog"] = watchdog
        if session is not UNSET:
            field_dict["session"] = session
        if detail is not UNSET:
            field_dict["detail"] = detail

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.session_state import SessionState  # noqa: PLC0415
        from ..models.watchdog_state import WatchdogState  # noqa: PLC0415

        d = dict(src_dict)
        status = d.pop("status")

        def _parse_browser(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        browser = _parse_browser(d.pop("browser", UNSET))

        def _parse_watchdog(data: object) -> None | Unset | WatchdogState:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                watchdog_type_0 = WatchdogState.from_dict(data)

                return watchdog_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | Unset | WatchdogState, data)

        watchdog = _parse_watchdog(d.pop("watchdog", UNSET))

        def _parse_session(data: object) -> None | SessionState | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                session_type_0 = SessionState.from_dict(data)

                return session_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | SessionState | Unset, data)

        session = _parse_session(d.pop("session", UNSET))

        def _parse_detail(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        detail = _parse_detail(d.pop("detail", UNSET))

        health = cls(
            status=status,
            browser=browser,
            watchdog=watchdog,
            session=session,
            detail=detail,
        )

        health.additional_properties = d
        return health

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
