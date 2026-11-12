from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.watcher_artist import WatcherArtist
    from ..models.watcher_info_last_pass_type_0 import WatcherInfoLastPassType0


T = TypeVar("T", bound="WatcherInfo")


@_attrs_define
class WatcherInfo:
    """
    Attributes:
        enabled (bool):
        interval (int):
        max_artists_per_pass (int | Unset):  Default: 100.
        auto_playlist (None | str | Unset):
        auto_add_active (bool | Unset):  Default: False.
        watched (int | Unset):  Default: 0.
        mapped (int | Unset):  Default: 0.
        unmapped (int | Unset):  Default: 0.
        artists (list[WatcherArtist] | Unset):
        last_pass (None | Unset | WatcherInfoLastPassType0):
    """

    enabled: bool
    interval: int
    max_artists_per_pass: int | Unset = 100
    auto_playlist: None | str | Unset = UNSET
    auto_add_active: bool | Unset = False
    watched: int | Unset = 0
    mapped: int | Unset = 0
    unmapped: int | Unset = 0
    artists: list[WatcherArtist] | Unset = UNSET
    last_pass: None | Unset | WatcherInfoLastPassType0 = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.watcher_info_last_pass_type_0 import WatcherInfoLastPassType0  # noqa: PLC0415

        enabled = self.enabled

        interval = self.interval

        max_artists_per_pass = self.max_artists_per_pass

        auto_playlist: None | str | Unset
        if isinstance(self.auto_playlist, Unset):
            auto_playlist = UNSET
        else:
            auto_playlist = self.auto_playlist

        auto_add_active = self.auto_add_active

        watched = self.watched

        mapped = self.mapped

        unmapped = self.unmapped

        artists: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.artists, Unset):
            artists = []
            for artists_item_data in self.artists:
                artists_item = artists_item_data.to_dict()
                artists.append(artists_item)

        last_pass: dict[str, Any] | None | Unset
        if isinstance(self.last_pass, Unset):
            last_pass = UNSET
        elif isinstance(self.last_pass, WatcherInfoLastPassType0):
            last_pass = self.last_pass.to_dict()
        else:
            last_pass = self.last_pass

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "enabled": enabled,
                "interval": interval,
            }
        )
        if max_artists_per_pass is not UNSET:
            field_dict["max_artists_per_pass"] = max_artists_per_pass
        if auto_playlist is not UNSET:
            field_dict["auto_playlist"] = auto_playlist
        if auto_add_active is not UNSET:
            field_dict["auto_add_active"] = auto_add_active
        if watched is not UNSET:
            field_dict["watched"] = watched
        if mapped is not UNSET:
            field_dict["mapped"] = mapped
        if unmapped is not UNSET:
            field_dict["unmapped"] = unmapped
        if artists is not UNSET:
            field_dict["artists"] = artists
        if last_pass is not UNSET:
            field_dict["last_pass"] = last_pass

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.watcher_artist import WatcherArtist  # noqa: PLC0415
        from ..models.watcher_info_last_pass_type_0 import WatcherInfoLastPassType0  # noqa: PLC0415

        d = dict(src_dict)
        enabled = d.pop("enabled")

        interval = d.pop("interval")

        max_artists_per_pass = d.pop("max_artists_per_pass", UNSET)

        def _parse_auto_playlist(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        auto_playlist = _parse_auto_playlist(d.pop("auto_playlist", UNSET))

        auto_add_active = d.pop("auto_add_active", UNSET)

        watched = d.pop("watched", UNSET)

        mapped = d.pop("mapped", UNSET)

        unmapped = d.pop("unmapped", UNSET)

        _artists = d.pop("artists", UNSET)
        artists: list[WatcherArtist] | Unset = UNSET
        if _artists is not UNSET:
            artists = []
            for artists_item_data in _artists:
                artists_item = WatcherArtist.from_dict(artists_item_data)

                artists.append(artists_item)

        def _parse_last_pass(data: object) -> None | Unset | WatcherInfoLastPassType0:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                last_pass_type_0 = WatcherInfoLastPassType0.from_dict(data)

                return last_pass_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | Unset | WatcherInfoLastPassType0, data)

        last_pass = _parse_last_pass(d.pop("last_pass", UNSET))

        watcher_info = cls(
            enabled=enabled,
            interval=interval,
            max_artists_per_pass=max_artists_per_pass,
            auto_playlist=auto_playlist,
            auto_add_active=auto_add_active,
            watched=watched,
            mapped=mapped,
            unmapped=unmapped,
            artists=artists,
            last_pass=last_pass,
        )

        watcher_info.additional_properties = d
        return watcher_info

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
