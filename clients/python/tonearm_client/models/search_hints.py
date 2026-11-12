from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.search_hints_hints_item import SearchHintsHintsItem


T = TypeVar("T", bound="SearchHints")


@_attrs_define
class SearchHints:
    """
    Attributes:
        hints (list[SearchHintsHintsItem]):
    """

    hints: list[SearchHintsHintsItem]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        hints = []
        for hints_item_data in self.hints:
            hints_item = hints_item_data.to_dict()
            hints.append(hints_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "hints": hints,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.search_hints_hints_item import SearchHintsHintsItem  # noqa: PLC0415

        d = dict(src_dict)
        hints = []
        _hints = d.pop("hints")
        for hints_item_data in _hints:
            hints_item = SearchHintsHintsItem.from_dict(hints_item_data)

            hints.append(hints_item)

        search_hints = cls(
            hints=hints,
        )

        search_hints.additional_properties = d
        return search_hints

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
