from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.debug_info_recent_calls_item import DebugInfoRecentCallsItem
    from ..models.debug_info_renderer import DebugInfoRenderer
    from ..models.debug_info_webhooks_type_0 import DebugInfoWebhooksType0


T = TypeVar("T", bound="DebugInfo")


@_attrs_define
class DebugInfo:
    """
    Attributes:
        renderer (DebugInfoRenderer):
        recent_calls (list[DebugInfoRecentCallsItem]):
        tab_url (None | str | Unset):
        webhooks (DebugInfoWebhooksType0 | None | Unset):
        note (None | str | Unset):
    """

    renderer: DebugInfoRenderer
    recent_calls: list[DebugInfoRecentCallsItem]
    tab_url: None | str | Unset = UNSET
    webhooks: DebugInfoWebhooksType0 | None | Unset = UNSET
    note: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.debug_info_webhooks_type_0 import DebugInfoWebhooksType0  # noqa: PLC0415

        renderer = self.renderer.to_dict()

        recent_calls = []
        for recent_calls_item_data in self.recent_calls:
            recent_calls_item = recent_calls_item_data.to_dict()
            recent_calls.append(recent_calls_item)

        tab_url: None | str | Unset
        if isinstance(self.tab_url, Unset):
            tab_url = UNSET
        else:
            tab_url = self.tab_url

        webhooks: dict[str, Any] | None | Unset
        if isinstance(self.webhooks, Unset):
            webhooks = UNSET
        elif isinstance(self.webhooks, DebugInfoWebhooksType0):
            webhooks = self.webhooks.to_dict()
        else:
            webhooks = self.webhooks

        note: None | str | Unset
        if isinstance(self.note, Unset):
            note = UNSET
        else:
            note = self.note

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "renderer": renderer,
                "recent_calls": recent_calls,
            }
        )
        if tab_url is not UNSET:
            field_dict["tab_url"] = tab_url
        if webhooks is not UNSET:
            field_dict["webhooks"] = webhooks
        if note is not UNSET:
            field_dict["note"] = note

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.debug_info_recent_calls_item import DebugInfoRecentCallsItem  # noqa: PLC0415
        from ..models.debug_info_renderer import DebugInfoRenderer  # noqa: PLC0415
        from ..models.debug_info_webhooks_type_0 import DebugInfoWebhooksType0  # noqa: PLC0415

        d = dict(src_dict)
        renderer = DebugInfoRenderer.from_dict(d.pop("renderer"))

        recent_calls = []
        _recent_calls = d.pop("recent_calls")
        for recent_calls_item_data in _recent_calls:
            recent_calls_item = DebugInfoRecentCallsItem.from_dict(recent_calls_item_data)

            recent_calls.append(recent_calls_item)

        def _parse_tab_url(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        tab_url = _parse_tab_url(d.pop("tab_url", UNSET))

        def _parse_webhooks(data: object) -> DebugInfoWebhooksType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                webhooks_type_0 = DebugInfoWebhooksType0.from_dict(data)

                return webhooks_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(DebugInfoWebhooksType0 | None | Unset, data)

        webhooks = _parse_webhooks(d.pop("webhooks", UNSET))

        def _parse_note(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        note = _parse_note(d.pop("note", UNSET))

        debug_info = cls(
            renderer=renderer,
            recent_calls=recent_calls,
            tab_url=tab_url,
            webhooks=webhooks,
            note=note,
        )

        debug_info.additional_properties = d
        return debug_info

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
