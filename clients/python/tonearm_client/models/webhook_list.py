from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.webhook_hook import WebhookHook
    from ..models.webhook_list_recent_item import WebhookListRecentItem


T = TypeVar("T", bound="WebhookList")


@_attrs_define
class WebhookList:
    """
    Attributes:
        enabled (bool):
        hooks (list[WebhookHook]):
        pending (int | Unset):  Default: 0.
        recent (list[WebhookListRecentItem] | Unset):
        note (None | str | Unset):
    """

    enabled: bool
    hooks: list[WebhookHook]
    pending: int | Unset = 0
    recent: list[WebhookListRecentItem] | Unset = UNSET
    note: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        enabled = self.enabled

        hooks = []
        for hooks_item_data in self.hooks:
            hooks_item = hooks_item_data.to_dict()
            hooks.append(hooks_item)

        pending = self.pending

        recent: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.recent, Unset):
            recent = []
            for recent_item_data in self.recent:
                recent_item = recent_item_data.to_dict()
                recent.append(recent_item)

        note: None | str | Unset
        if isinstance(self.note, Unset):
            note = UNSET
        else:
            note = self.note

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "enabled": enabled,
                "hooks": hooks,
            }
        )
        if pending is not UNSET:
            field_dict["pending"] = pending
        if recent is not UNSET:
            field_dict["recent"] = recent
        if note is not UNSET:
            field_dict["note"] = note

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.webhook_hook import WebhookHook  # noqa: PLC0415
        from ..models.webhook_list_recent_item import WebhookListRecentItem  # noqa: PLC0415

        d = dict(src_dict)
        enabled = d.pop("enabled")

        hooks = []
        _hooks = d.pop("hooks")
        for hooks_item_data in _hooks:
            hooks_item = WebhookHook.from_dict(hooks_item_data)

            hooks.append(hooks_item)

        pending = d.pop("pending", UNSET)

        _recent = d.pop("recent", UNSET)
        recent: list[WebhookListRecentItem] | Unset = UNSET
        if _recent is not UNSET:
            recent = []
            for recent_item_data in _recent:
                recent_item = WebhookListRecentItem.from_dict(recent_item_data)

                recent.append(recent_item)

        def _parse_note(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        note = _parse_note(d.pop("note", UNSET))

        webhook_list = cls(
            enabled=enabled,
            hooks=hooks,
            pending=pending,
            recent=recent,
            note=note,
        )

        webhook_list.additional_properties = d
        return webhook_list

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
