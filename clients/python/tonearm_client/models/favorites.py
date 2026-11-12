from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.song_row import SongRow


T = TypeVar("T", bound="Favorites")


@_attrs_define
class Favorites:
    """
    Attributes:
        count (int):
        playlist_id (str):
        tracks (list[SongRow]):
    """

    count: int
    playlist_id: str
    tracks: list[SongRow]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        count = self.count

        playlist_id = self.playlist_id

        tracks = []
        for tracks_item_data in self.tracks:
            tracks_item = tracks_item_data.to_dict()
            tracks.append(tracks_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "count": count,
                "playlist_id": playlist_id,
                "tracks": tracks,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.song_row import SongRow  # noqa: PLC0415

        d = dict(src_dict)
        count = d.pop("count")

        playlist_id = d.pop("playlist_id")

        tracks = []
        _tracks = d.pop("tracks")
        for tracks_item_data in _tracks:
            tracks_item = SongRow.from_dict(tracks_item_data)

            tracks.append(tracks_item)

        favorites = cls(
            count=count,
            playlist_id=playlist_id,
            tracks=tracks,
        )

        favorites.additional_properties = d
        return favorites

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
