from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.item_row import ItemRow


T = TypeVar("T", bound="LibrarySearchApiLibrarySearchGetResponseLibrarySearchApiLibrarySearchGet")


@_attrs_define
class LibrarySearchApiLibrarySearchGetResponseLibrarySearchApiLibrarySearchGet:
    additional_properties: dict[str, list[ItemRow]] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:

        field_dict: dict[str, Any] = {}
        for prop_name, prop in self.additional_properties.items():
            field_dict[prop_name] = []
            for additional_property_item_data in prop:
                additional_property_item = additional_property_item_data.to_dict()
                field_dict[prop_name].append(additional_property_item)

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.item_row import ItemRow  # noqa: PLC0415

        d = dict(src_dict)
        library_search_api_library_search_get_response_library_search_api_library_search_get = cls()

        additional_properties = {}
        for prop_name, prop_dict in d.items():
            additional_property = []
            _additional_property = prop_dict
            for additional_property_item_data in _additional_property:
                additional_property_item = ItemRow.from_dict(additional_property_item_data)

                additional_property.append(additional_property_item)

            additional_properties[prop_name] = additional_property

        library_search_api_library_search_get_response_library_search_api_library_search_get.additional_properties = (
            additional_properties
        )
        return library_search_api_library_search_get_response_library_search_api_library_search_get

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> list[ItemRow]:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: list[ItemRow]) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
