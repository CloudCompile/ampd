from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.smartlist import Smartlist


T = TypeVar("T", bound="Smartlists")


@_attrs_define
class Smartlists:
    """
    Attributes:
        enabled (bool):
        items (list[Smartlist]):
        scheduler_interval (int | Unset):  Default: 0.
    """

    enabled: bool
    items: list[Smartlist]
    scheduler_interval: int | Unset = 0
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        enabled = self.enabled

        items = []
        for items_item_data in self.items:
            items_item = items_item_data.to_dict()
            items.append(items_item)

        scheduler_interval = self.scheduler_interval

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "enabled": enabled,
                "items": items,
            }
        )
        if scheduler_interval is not UNSET:
            field_dict["scheduler_interval"] = scheduler_interval

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.smartlist import Smartlist  # noqa: PLC0415

        d = dict(src_dict)
        enabled = d.pop("enabled")

        items = []
        _items = d.pop("items")
        for items_item_data in _items:
            items_item = Smartlist.from_dict(items_item_data)

            items.append(items_item)

        scheduler_interval = d.pop("scheduler_interval", UNSET)

        smartlists = cls(
            enabled=enabled,
            items=items,
            scheduler_interval=scheduler_interval,
        )

        smartlists.additional_properties = d
        return smartlists

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
