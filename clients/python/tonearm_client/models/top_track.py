from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="TopTrack")


@_attrs_define
class TopTrack:
    """
    Attributes:
        id (str):
        plays (int):
        title (None | str | Unset):
        artist (None | str | Unset):
    """

    id: str
    plays: int
    title: None | str | Unset = UNSET
    artist: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        plays = self.plays

        title: None | str | Unset
        if isinstance(self.title, Unset):
            title = UNSET
        else:
            title = self.title

        artist: None | str | Unset
        if isinstance(self.artist, Unset):
            artist = UNSET
        else:
            artist = self.artist

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "plays": plays,
            }
        )
        if title is not UNSET:
            field_dict["title"] = title
        if artist is not UNSET:
            field_dict["artist"] = artist

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id")

        plays = d.pop("plays")

        def _parse_title(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        title = _parse_title(d.pop("title", UNSET))

        def _parse_artist(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        artist = _parse_artist(d.pop("artist", UNSET))

        top_track = cls(
            id=id,
            plays=plays,
            title=title,
            artist=artist,
        )

        top_track.additional_properties = d
        return top_track

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
