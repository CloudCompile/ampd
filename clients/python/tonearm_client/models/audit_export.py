from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.audit_entry import AuditEntry


T = TypeVar("T", bound="AuditExport")


@_attrs_define
class AuditExport:
    """
    Attributes:
        total (int):
        count (int):
        items (list[AuditEntry]):
        next_offset (int | None | Unset):
        source (str | Unset):  Default: 'store'.
    """

    total: int
    count: int
    items: list[AuditEntry]
    next_offset: int | None | Unset = UNSET
    source: str | Unset = "store"
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        total = self.total

        count = self.count

        items = []
        for items_item_data in self.items:
            items_item = items_item_data.to_dict()
            items.append(items_item)

        next_offset: int | None | Unset
        if isinstance(self.next_offset, Unset):
            next_offset = UNSET
        else:
            next_offset = self.next_offset

        source = self.source

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "total": total,
                "count": count,
                "items": items,
            }
        )
        if next_offset is not UNSET:
            field_dict["next_offset"] = next_offset
        if source is not UNSET:
            field_dict["source"] = source

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.audit_entry import AuditEntry  # noqa: PLC0415

        d = dict(src_dict)
        total = d.pop("total")

        count = d.pop("count")

        items = []
        _items = d.pop("items")
        for items_item_data in _items:
            items_item = AuditEntry.from_dict(items_item_data)

            items.append(items_item)

        def _parse_next_offset(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        next_offset = _parse_next_offset(d.pop("next_offset", UNSET))

        source = d.pop("source", UNSET)

        audit_export = cls(
            total=total,
            count=count,
            items=items,
            next_offset=next_offset,
            source=source,
        )

        audit_export.additional_properties = d
        return audit_export

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
