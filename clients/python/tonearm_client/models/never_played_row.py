from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.never_played_row_attributes import NeverPlayedRowAttributes


T = TypeVar("T", bound="NeverPlayedRow")


@_attrs_define
class NeverPlayedRow:
    """
    Attributes:
        id (None | str | Unset):
        library_id (None | str | Unset):
        catalog_id (None | str | Unset):
        name (None | str | Unset):
        artist (None | str | Unset):
        album (None | str | Unset):
        artwork (None | str | Unset):
        duration_ms (int | None | Unset):
        type_ (None | str | Unset):
        track_number (int | None | Unset):
        play_count (int | None | Unset):
        release_date (None | str | Unset):
        genres (list[str] | None | Unset):
        attributes (NeverPlayedRowAttributes | Unset):
    """

    id: None | str | Unset = UNSET
    library_id: None | str | Unset = UNSET
    catalog_id: None | str | Unset = UNSET
    name: None | str | Unset = UNSET
    artist: None | str | Unset = UNSET
    album: None | str | Unset = UNSET
    artwork: None | str | Unset = UNSET
    duration_ms: int | None | Unset = UNSET
    type_: None | str | Unset = UNSET
    track_number: int | None | Unset = UNSET
    play_count: int | None | Unset = UNSET
    release_date: None | str | Unset = UNSET
    genres: list[str] | None | Unset = UNSET
    attributes: NeverPlayedRowAttributes | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id: None | str | Unset
        if isinstance(self.id, Unset):
            id = UNSET
        else:
            id = self.id

        library_id: None | str | Unset
        if isinstance(self.library_id, Unset):
            library_id = UNSET
        else:
            library_id = self.library_id

        catalog_id: None | str | Unset
        if isinstance(self.catalog_id, Unset):
            catalog_id = UNSET
        else:
            catalog_id = self.catalog_id

        name: None | str | Unset
        if isinstance(self.name, Unset):
            name = UNSET
        else:
            name = self.name

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

        type_: None | str | Unset
        if isinstance(self.type_, Unset):
            type_ = UNSET
        else:
            type_ = self.type_

        track_number: int | None | Unset
        if isinstance(self.track_number, Unset):
            track_number = UNSET
        else:
            track_number = self.track_number

        play_count: int | None | Unset
        if isinstance(self.play_count, Unset):
            play_count = UNSET
        else:
            play_count = self.play_count

        release_date: None | str | Unset
        if isinstance(self.release_date, Unset):
            release_date = UNSET
        else:
            release_date = self.release_date

        genres: list[str] | None | Unset
        if isinstance(self.genres, Unset):
            genres = UNSET
        elif isinstance(self.genres, list):
            genres = self.genres

        else:
            genres = self.genres

        attributes: dict[str, Any] | Unset = UNSET
        if not isinstance(self.attributes, Unset):
            attributes = self.attributes.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if library_id is not UNSET:
            field_dict["library_id"] = library_id
        if catalog_id is not UNSET:
            field_dict["catalog_id"] = catalog_id
        if name is not UNSET:
            field_dict["name"] = name
        if artist is not UNSET:
            field_dict["artist"] = artist
        if album is not UNSET:
            field_dict["album"] = album
        if artwork is not UNSET:
            field_dict["artwork"] = artwork
        if duration_ms is not UNSET:
            field_dict["duration_ms"] = duration_ms
        if type_ is not UNSET:
            field_dict["type"] = type_
        if track_number is not UNSET:
            field_dict["track_number"] = track_number
        if play_count is not UNSET:
            field_dict["play_count"] = play_count
        if release_date is not UNSET:
            field_dict["release_date"] = release_date
        if genres is not UNSET:
            field_dict["genres"] = genres
        if attributes is not UNSET:
            field_dict["attributes"] = attributes

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.never_played_row_attributes import NeverPlayedRowAttributes  # noqa: PLC0415

        d = dict(src_dict)

        def _parse_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        id = _parse_id(d.pop("id", UNSET))

        def _parse_library_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        library_id = _parse_library_id(d.pop("library_id", UNSET))

        def _parse_catalog_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        catalog_id = _parse_catalog_id(d.pop("catalog_id", UNSET))

        def _parse_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        name = _parse_name(d.pop("name", UNSET))

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

        def _parse_type_(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        type_ = _parse_type_(d.pop("type", UNSET))

        def _parse_track_number(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        track_number = _parse_track_number(d.pop("track_number", UNSET))

        def _parse_play_count(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        play_count = _parse_play_count(d.pop("play_count", UNSET))

        def _parse_release_date(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        release_date = _parse_release_date(d.pop("release_date", UNSET))

        def _parse_genres(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                genres_type_0 = cast(list[str], data)

                return genres_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        genres = _parse_genres(d.pop("genres", UNSET))

        _attributes = d.pop("attributes", UNSET)
        attributes: NeverPlayedRowAttributes | Unset
        if isinstance(_attributes, Unset):
            attributes = UNSET
        else:
            attributes = NeverPlayedRowAttributes.from_dict(_attributes)

        never_played_row = cls(
            id=id,
            library_id=library_id,
            catalog_id=catalog_id,
            name=name,
            artist=artist,
            album=album,
            artwork=artwork,
            duration_ms=duration_ms,
            type_=type_,
            track_number=track_number,
            play_count=play_count,
            release_date=release_date,
            genres=genres,
            attributes=attributes,
        )

        never_played_row.additional_properties = d
        return never_played_row

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
