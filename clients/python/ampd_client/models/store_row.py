from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="StoreRow")


@_attrs_define
class StoreRow:
    """
    Attributes:
        library_id (str):
        catalog_id (None | str | Unset):
        name (None | str | Unset):
        artist (None | str | Unset):
        album (None | str | Unset):
        duration_ms (int | None | Unset):
        kind (None | str | Unset):
        first_seen (float | None | Unset):
        last_seen (float | None | Unset):
        last_changed (float | None | Unset):
    """

    library_id: str
    catalog_id: None | str | Unset = UNSET
    name: None | str | Unset = UNSET
    artist: None | str | Unset = UNSET
    album: None | str | Unset = UNSET
    duration_ms: int | None | Unset = UNSET
    kind: None | str | Unset = UNSET
    first_seen: float | None | Unset = UNSET
    last_seen: float | None | Unset = UNSET
    last_changed: float | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
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

        duration_ms: int | None | Unset
        if isinstance(self.duration_ms, Unset):
            duration_ms = UNSET
        else:
            duration_ms = self.duration_ms

        kind: None | str | Unset
        if isinstance(self.kind, Unset):
            kind = UNSET
        else:
            kind = self.kind

        first_seen: float | None | Unset
        if isinstance(self.first_seen, Unset):
            first_seen = UNSET
        else:
            first_seen = self.first_seen

        last_seen: float | None | Unset
        if isinstance(self.last_seen, Unset):
            last_seen = UNSET
        else:
            last_seen = self.last_seen

        last_changed: float | None | Unset
        if isinstance(self.last_changed, Unset):
            last_changed = UNSET
        else:
            last_changed = self.last_changed

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "library_id": library_id,
            }
        )
        if catalog_id is not UNSET:
            field_dict["catalog_id"] = catalog_id
        if name is not UNSET:
            field_dict["name"] = name
        if artist is not UNSET:
            field_dict["artist"] = artist
        if album is not UNSET:
            field_dict["album"] = album
        if duration_ms is not UNSET:
            field_dict["duration_ms"] = duration_ms
        if kind is not UNSET:
            field_dict["kind"] = kind
        if first_seen is not UNSET:
            field_dict["first_seen"] = first_seen
        if last_seen is not UNSET:
            field_dict["last_seen"] = last_seen
        if last_changed is not UNSET:
            field_dict["last_changed"] = last_changed

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        library_id = d.pop("library_id")

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

        def _parse_duration_ms(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        duration_ms = _parse_duration_ms(d.pop("duration_ms", UNSET))

        def _parse_kind(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        kind = _parse_kind(d.pop("kind", UNSET))

        def _parse_first_seen(data: object) -> float | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(float | None | Unset, data)

        first_seen = _parse_first_seen(d.pop("first_seen", UNSET))

        def _parse_last_seen(data: object) -> float | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(float | None | Unset, data)

        last_seen = _parse_last_seen(d.pop("last_seen", UNSET))

        def _parse_last_changed(data: object) -> float | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(float | None | Unset, data)

        last_changed = _parse_last_changed(d.pop("last_changed", UNSET))

        store_row = cls(
            library_id=library_id,
            catalog_id=catalog_id,
            name=name,
            artist=artist,
            album=album,
            duration_ms=duration_ms,
            kind=kind,
            first_seen=first_seen,
            last_seen=last_seen,
            last_changed=last_changed,
        )

        store_row.additional_properties = d
        return store_row

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
