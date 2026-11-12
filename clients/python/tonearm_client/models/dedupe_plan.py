from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.item_row import ItemRow


T = TypeVar("T", bound="DedupePlan")


@_attrs_define
class DedupePlan:
    """
    Attributes:
        library_size (int):
        duplicate_groups (int):
        removable_rows (int):
        groups (list[list[ItemRow]]):
        note (None | str | Unset):
    """

    library_size: int
    duplicate_groups: int
    removable_rows: int
    groups: list[list[ItemRow]]
    note: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        library_size = self.library_size

        duplicate_groups = self.duplicate_groups

        removable_rows = self.removable_rows

        groups = []
        for groups_item_data in self.groups:
            groups_item = []
            for groups_item_item_data in groups_item_data:
                groups_item_item = groups_item_item_data.to_dict()
                groups_item.append(groups_item_item)

            groups.append(groups_item)

        note: None | str | Unset
        if isinstance(self.note, Unset):
            note = UNSET
        else:
            note = self.note

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "library_size": library_size,
                "duplicate_groups": duplicate_groups,
                "removable_rows": removable_rows,
                "groups": groups,
            }
        )
        if note is not UNSET:
            field_dict["note"] = note

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.item_row import ItemRow  # noqa: PLC0415

        d = dict(src_dict)
        library_size = d.pop("library_size")

        duplicate_groups = d.pop("duplicate_groups")

        removable_rows = d.pop("removable_rows")

        groups = []
        _groups = d.pop("groups")
        for groups_item_data in _groups:
            groups_item = []
            _groups_item = groups_item_data
            for groups_item_item_data in _groups_item:
                groups_item_item = ItemRow.from_dict(groups_item_item_data)

                groups_item.append(groups_item_item)

            groups.append(groups_item)

        def _parse_note(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        note = _parse_note(d.pop("note", UNSET))

        dedupe_plan = cls(
            library_size=library_size,
            duplicate_groups=duplicate_groups,
            removable_rows=removable_rows,
            groups=groups,
            note=note,
        )

        dedupe_plan.additional_properties = d
        return dedupe_plan

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
