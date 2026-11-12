from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.webhook_hook_stats import WebhookHookStats


T = TypeVar("T", bound="WebhookHook")


@_attrs_define
class WebhookHook:
    """
    Attributes:
        id (str):
        url (str):
        events (list[str] | Unset):
        enabled (bool | Unset):  Default: True.
        has_secret (bool | Unset):  Default: False.
        created_at (float | None | Unset):
        stats (WebhookHookStats | Unset):
    """

    id: str
    url: str
    events: list[str] | Unset = UNSET
    enabled: bool | Unset = True
    has_secret: bool | Unset = False
    created_at: float | None | Unset = UNSET
    stats: WebhookHookStats | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        url = self.url

        events: list[str] | Unset = UNSET
        if not isinstance(self.events, Unset):
            events = self.events

        enabled = self.enabled

        has_secret = self.has_secret

        created_at: float | None | Unset
        if isinstance(self.created_at, Unset):
            created_at = UNSET
        else:
            created_at = self.created_at

        stats: dict[str, Any] | Unset = UNSET
        if not isinstance(self.stats, Unset):
            stats = self.stats.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "url": url,
            }
        )
        if events is not UNSET:
            field_dict["events"] = events
        if enabled is not UNSET:
            field_dict["enabled"] = enabled
        if has_secret is not UNSET:
            field_dict["has_secret"] = has_secret
        if created_at is not UNSET:
            field_dict["created_at"] = created_at
        if stats is not UNSET:
            field_dict["stats"] = stats

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.webhook_hook_stats import WebhookHookStats  # noqa: PLC0415

        d = dict(src_dict)
        id = d.pop("id")

        url = d.pop("url")

        events = cast(list[str], d.pop("events", UNSET))

        enabled = d.pop("enabled", UNSET)

        has_secret = d.pop("has_secret", UNSET)

        def _parse_created_at(data: object) -> float | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(float | None | Unset, data)

        created_at = _parse_created_at(d.pop("created_at", UNSET))

        _stats = d.pop("stats", UNSET)
        stats: WebhookHookStats | Unset
        if isinstance(_stats, Unset):
            stats = UNSET
        else:
            stats = WebhookHookStats.from_dict(_stats)

        webhook_hook = cls(
            id=id,
            url=url,
            events=events,
            enabled=enabled,
            has_secret=has_secret,
            created_at=created_at,
            stats=stats,
        )

        webhook_hook.additional_properties = d
        return webhook_hook

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
