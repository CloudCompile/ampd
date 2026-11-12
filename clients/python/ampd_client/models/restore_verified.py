from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="RestoreVerified")


@_attrs_define
class RestoreVerified:
    """
    Attributes:
        name (str):
        playlist_id (str):
        tracks (int):
    """

    name: str
    playlist_id: str
    tracks: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        playlist_id = self.playlist_id

        tracks = self.tracks

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
                "playlist_id": playlist_id,
                "tracks": tracks,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        name = d.pop("name")

        playlist_id = d.pop("playlist_id")

        tracks = d.pop("tracks")

        restore_verified = cls(
            name=name,
            playlist_id=playlist_id,
            tracks=tracks,
        )

        restore_verified.additional_properties = d
        return restore_verified

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
