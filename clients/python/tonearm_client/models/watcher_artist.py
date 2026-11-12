from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="WatcherArtist")


@_attrs_define
class WatcherArtist:
    """One row of watcher state: the mapping cache + newest release seen.

    Attributes:
        artist_id (str):
        artist_name (None | str | Unset):
        catalog_artist_id (None | str | Unset):
        catalog_artist_name (None | str | Unset):
        last_album_id (None | str | Unset):
        last_album_name (None | str | Unset):
        last_release_date (None | str | Unset):
        checked_at (float | None | Unset):
    """

    artist_id: str
    artist_name: None | str | Unset = UNSET
    catalog_artist_id: None | str | Unset = UNSET
    catalog_artist_name: None | str | Unset = UNSET
    last_album_id: None | str | Unset = UNSET
    last_album_name: None | str | Unset = UNSET
    last_release_date: None | str | Unset = UNSET
    checked_at: float | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        artist_id = self.artist_id

        artist_name: None | str | Unset
        if isinstance(self.artist_name, Unset):
            artist_name = UNSET
        else:
            artist_name = self.artist_name

        catalog_artist_id: None | str | Unset
        if isinstance(self.catalog_artist_id, Unset):
            catalog_artist_id = UNSET
        else:
            catalog_artist_id = self.catalog_artist_id

        catalog_artist_name: None | str | Unset
        if isinstance(self.catalog_artist_name, Unset):
            catalog_artist_name = UNSET
        else:
            catalog_artist_name = self.catalog_artist_name

        last_album_id: None | str | Unset
        if isinstance(self.last_album_id, Unset):
            last_album_id = UNSET
        else:
            last_album_id = self.last_album_id

        last_album_name: None | str | Unset
        if isinstance(self.last_album_name, Unset):
            last_album_name = UNSET
        else:
            last_album_name = self.last_album_name

        last_release_date: None | str | Unset
        if isinstance(self.last_release_date, Unset):
            last_release_date = UNSET
        else:
            last_release_date = self.last_release_date

        checked_at: float | None | Unset
        if isinstance(self.checked_at, Unset):
            checked_at = UNSET
        else:
            checked_at = self.checked_at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "artist_id": artist_id,
            }
        )
        if artist_name is not UNSET:
            field_dict["artist_name"] = artist_name
        if catalog_artist_id is not UNSET:
            field_dict["catalog_artist_id"] = catalog_artist_id
        if catalog_artist_name is not UNSET:
            field_dict["catalog_artist_name"] = catalog_artist_name
        if last_album_id is not UNSET:
            field_dict["last_album_id"] = last_album_id
        if last_album_name is not UNSET:
            field_dict["last_album_name"] = last_album_name
        if last_release_date is not UNSET:
            field_dict["last_release_date"] = last_release_date
        if checked_at is not UNSET:
            field_dict["checked_at"] = checked_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        artist_id = d.pop("artist_id")

        def _parse_artist_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        artist_name = _parse_artist_name(d.pop("artist_name", UNSET))

        def _parse_catalog_artist_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        catalog_artist_id = _parse_catalog_artist_id(d.pop("catalog_artist_id", UNSET))

        def _parse_catalog_artist_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        catalog_artist_name = _parse_catalog_artist_name(d.pop("catalog_artist_name", UNSET))

        def _parse_last_album_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        last_album_id = _parse_last_album_id(d.pop("last_album_id", UNSET))

        def _parse_last_album_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        last_album_name = _parse_last_album_name(d.pop("last_album_name", UNSET))

        def _parse_last_release_date(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        last_release_date = _parse_last_release_date(d.pop("last_release_date", UNSET))

        def _parse_checked_at(data: object) -> float | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(float | None | Unset, data)

        checked_at = _parse_checked_at(d.pop("checked_at", UNSET))

        watcher_artist = cls(
            artist_id=artist_id,
            artist_name=artist_name,
            catalog_artist_id=catalog_artist_id,
            catalog_artist_name=catalog_artist_name,
            last_album_id=last_album_id,
            last_album_name=last_album_name,
            last_release_date=last_release_date,
            checked_at=checked_at,
        )

        watcher_artist.additional_properties = d
        return watcher_artist

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
