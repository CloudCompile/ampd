from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PlayRow")


@_attrs_define
class PlayRow:
    """
    Attributes:
        id (str):
        played_at (str):
        title (None | str | Unset):
        artist (None | str | Unset):
        album (None | str | Unset):
        artwork (None | str | Unset):
        duration_ms (int | None | Unset):
    """

    id: str
    played_at: str
    title: None | str | Unset = UNSET
    artist: None | str | Unset = UNSET
    album: None | str | Unset = UNSET
    artwork: None | str | Unset = UNSET
    duration_ms: int | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        played_at = self.played_at

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

        album: None | str | Unset
        if isinstance(self.album, Unset):
            album = UNSET
        else:
            album = self.album

        artwork: None | str | Unset
        if isinstance(self.artwork, Unset):
            artwork = UNSET
        else:
            artwork = self.artwork

        duration_ms: int | None | Unset
        if isinstance(self.duration_ms, Unset):
            duration_ms = UNSET
        else:
            duration_ms = self.duration_ms

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "played_at": played_at,
            }
        )
        if title is not UNSET:
            field_dict["title"] = title
        if artist is not UNSET:
            field_dict["artist"] = artist
        if album is not UNSET:
            field_dict["album"] = album
        if artwork is not UNSET:
            field_dict["artwork"] = artwork
        if duration_ms is not UNSET:
            field_dict["duration_ms"] = duration_ms

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id")

        played_at = d.pop("played_at")

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

        def _parse_album(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        album = _parse_album(d.pop("album", UNSET))

        def _parse_artwork(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        artwork = _parse_artwork(d.pop("artwork", UNSET))

        def _parse_duration_ms(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        duration_ms = _parse_duration_ms(d.pop("duration_ms", UNSET))

        play_row = cls(
            id=id,
            played_at=played_at,
            title=title,
            artist=artist,
            album=album,
            artwork=artwork,
            duration_ms=duration_ms,
        )

        play_row.additional_properties = d
        return play_row

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
