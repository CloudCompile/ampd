from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.top_artist import TopArtist
    from ..models.top_track import TopTrack


T = TypeVar("T", bound="Stats")


@_attrs_define
class Stats:
    """
    Attributes:
        window_since (float):
        total_plays (int):
        top_tracks (list[TopTrack]):
        top_artists (list[TopArtist]):
    """

    window_since: float
    total_plays: int
    top_tracks: list[TopTrack]
    top_artists: list[TopArtist]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        window_since = self.window_since

        total_plays = self.total_plays

        top_tracks = []
        for top_tracks_item_data in self.top_tracks:
            top_tracks_item = top_tracks_item_data.to_dict()
            top_tracks.append(top_tracks_item)

        top_artists = []
        for top_artists_item_data in self.top_artists:
            top_artists_item = top_artists_item_data.to_dict()
            top_artists.append(top_artists_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "window_since": window_since,
                "total_plays": total_plays,
                "top_tracks": top_tracks,
                "top_artists": top_artists,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.top_artist import TopArtist  # noqa: PLC0415
        from ..models.top_track import TopTrack  # noqa: PLC0415

        d = dict(src_dict)
        window_since = d.pop("window_since")

        total_plays = d.pop("total_plays")

        top_tracks = []
        _top_tracks = d.pop("top_tracks")
        for top_tracks_item_data in _top_tracks:
            top_tracks_item = TopTrack.from_dict(top_tracks_item_data)

            top_tracks.append(top_tracks_item)

        top_artists = []
        _top_artists = d.pop("top_artists")
        for top_artists_item_data in _top_artists:
            top_artists_item = TopArtist.from_dict(top_artists_item_data)

            top_artists.append(top_artists_item)

        stats = cls(
            window_since=window_since,
            total_plays=total_plays,
            top_tracks=top_tracks,
            top_artists=top_artists,
        )

        stats.additional_properties = d
        return stats

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
