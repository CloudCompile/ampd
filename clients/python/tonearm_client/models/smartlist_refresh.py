from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="SmartlistRefresh")


@_attrs_define
class SmartlistRefresh:
    """
    Attributes:
        id (str):
        name (str):
        playlist_id (str):
        created (bool | Unset):  Default: False.
        count (int | Unset):  Default: 0.
    """

    id: str
    name: str
    playlist_id: str
    created: bool | Unset = False
    count: int | Unset = 0
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        name = self.name

        playlist_id = self.playlist_id

        created = self.created

        count = self.count

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "name": name,
                "playlist_id": playlist_id,
            }
        )
        if created is not UNSET:
            field_dict["created"] = created
        if count is not UNSET:
            field_dict["count"] = count

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id")

        name = d.pop("name")

        playlist_id = d.pop("playlist_id")

        created = d.pop("created", UNSET)

        count = d.pop("count", UNSET)

        smartlist_refresh = cls(
            id=id,
            name=name,
            playlist_id=playlist_id,
            created=created,
            count=count,
        )

        smartlist_refresh.additional_properties = d
        return smartlist_refresh

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
