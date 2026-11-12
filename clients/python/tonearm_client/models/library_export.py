from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.export_playlist import ExportPlaylist
    from ..models.song_row import SongRow


T = TypeVar("T", bound="LibraryExport")


@_attrs_define
class LibraryExport:
    """
    Attributes:
        exported_at (str):
        song_count (int):
        songs (list[SongRow]):
        playlist_count (int):
        playlists (list[ExportPlaylist]):
    """

    exported_at: str
    song_count: int
    songs: list[SongRow]
    playlist_count: int
    playlists: list[ExportPlaylist]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        exported_at = self.exported_at

        song_count = self.song_count

        songs = []
        for songs_item_data in self.songs:
            songs_item = songs_item_data.to_dict()
            songs.append(songs_item)

        playlist_count = self.playlist_count

        playlists = []
        for playlists_item_data in self.playlists:
            playlists_item = playlists_item_data.to_dict()
            playlists.append(playlists_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "exported_at": exported_at,
                "song_count": song_count,
                "songs": songs,
                "playlist_count": playlist_count,
                "playlists": playlists,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.export_playlist import ExportPlaylist  # noqa: PLC0415
        from ..models.song_row import SongRow  # noqa: PLC0415

        d = dict(src_dict)
        exported_at = d.pop("exported_at")

        song_count = d.pop("song_count")

        songs = []
        _songs = d.pop("songs")
        for songs_item_data in _songs:
            songs_item = SongRow.from_dict(songs_item_data)

            songs.append(songs_item)

        playlist_count = d.pop("playlist_count")

        playlists = []
        _playlists = d.pop("playlists")
        for playlists_item_data in _playlists:
            playlists_item = ExportPlaylist.from_dict(playlists_item_data)

            playlists.append(playlists_item)

        library_export = cls(
            exported_at=exported_at,
            song_count=song_count,
            songs=songs,
            playlist_count=playlist_count,
            playlists=playlists,
        )

        library_export.additional_properties = d
        return library_export

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
