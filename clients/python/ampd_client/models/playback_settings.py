from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PlaybackSettings")


@_attrs_define
class PlaybackSettings:
    """
    Attributes:
        shuffle (None | str | Unset):
        repeat (int | None | Unset):
        volume (float | None | Unset):
        is_playing (bool | None | Unset):
    """

    shuffle: None | str | Unset = UNSET
    repeat: int | None | Unset = UNSET
    volume: float | None | Unset = UNSET
    is_playing: bool | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        shuffle: None | str | Unset
        if isinstance(self.shuffle, Unset):
            shuffle = UNSET
        else:
            shuffle = self.shuffle

        repeat: int | None | Unset
        if isinstance(self.repeat, Unset):
            repeat = UNSET
        else:
            repeat = self.repeat

        volume: float | None | Unset
        if isinstance(self.volume, Unset):
            volume = UNSET
        else:
            volume = self.volume

        is_playing: bool | None | Unset
        if isinstance(self.is_playing, Unset):
            is_playing = UNSET
        else:
            is_playing = self.is_playing

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if shuffle is not UNSET:
            field_dict["shuffle"] = shuffle
        if repeat is not UNSET:
            field_dict["repeat"] = repeat
        if volume is not UNSET:
            field_dict["volume"] = volume
        if is_playing is not UNSET:
            field_dict["isPlaying"] = is_playing

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_shuffle(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        shuffle = _parse_shuffle(d.pop("shuffle", UNSET))

        def _parse_repeat(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        repeat = _parse_repeat(d.pop("repeat", UNSET))

        def _parse_volume(data: object) -> float | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(float | None | Unset, data)

        volume = _parse_volume(d.pop("volume", UNSET))

        def _parse_is_playing(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        is_playing = _parse_is_playing(d.pop("isPlaying", UNSET))

        playback_settings = cls(
            shuffle=shuffle,
            repeat=repeat,
            volume=volume,
            is_playing=is_playing,
        )

        playback_settings.additional_properties = d
        return playback_settings

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
