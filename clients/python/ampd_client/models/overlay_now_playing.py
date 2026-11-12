from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="OverlayNowPlaying")


@_attrs_define
class OverlayNowPlaying:
    """OBS overlay payload — NowPlaying + the playing item's id (what the
    SSE `update` events carry), so overlays can also resolve lyrics/art.

        Attributes:
            is_playing (bool):
            state (float | int | None | Unset):
            title (None | str | Unset):
            artist (None | str | Unset):
            album (None | str | Unset):
            duration_ms (int | None | Unset):
            artwork_url (None | str | Unset):
            progress (float | None | Unset):
            elapsed_ms (int | None | Unset):
            id (None | str | Unset):
    """

    is_playing: bool
    state: float | int | None | Unset = UNSET
    title: None | str | Unset = UNSET
    artist: None | str | Unset = UNSET
    album: None | str | Unset = UNSET
    duration_ms: int | None | Unset = UNSET
    artwork_url: None | str | Unset = UNSET
    progress: float | None | Unset = UNSET
    elapsed_ms: int | None | Unset = UNSET
    id: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        is_playing = self.is_playing

        state: float | int | None | Unset
        if isinstance(self.state, Unset):
            state = UNSET
        else:
            state = self.state

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

        duration_ms: int | None | Unset
        if isinstance(self.duration_ms, Unset):
            duration_ms = UNSET
        else:
            duration_ms = self.duration_ms

        artwork_url: None | str | Unset
        if isinstance(self.artwork_url, Unset):
            artwork_url = UNSET
        else:
            artwork_url = self.artwork_url

        progress: float | None | Unset
        if isinstance(self.progress, Unset):
            progress = UNSET
        else:
            progress = self.progress

        elapsed_ms: int | None | Unset
        if isinstance(self.elapsed_ms, Unset):
            elapsed_ms = UNSET
        else:
            elapsed_ms = self.elapsed_ms

        id: None | str | Unset
        if isinstance(self.id, Unset):
            id = UNSET
        else:
            id = self.id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "isPlaying": is_playing,
            }
        )
        if state is not UNSET:
            field_dict["state"] = state
        if title is not UNSET:
            field_dict["title"] = title
        if artist is not UNSET:
            field_dict["artist"] = artist
        if album is not UNSET:
            field_dict["album"] = album
        if duration_ms is not UNSET:
            field_dict["durationMs"] = duration_ms
        if artwork_url is not UNSET:
            field_dict["artworkUrl"] = artwork_url
        if progress is not UNSET:
            field_dict["progress"] = progress
        if elapsed_ms is not UNSET:
            field_dict["elapsedMs"] = elapsed_ms
        if id is not UNSET:
            field_dict["id"] = id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        is_playing = d.pop("isPlaying")

        def _parse_state(data: object) -> float | int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(float | int | None | Unset, data)

        state = _parse_state(d.pop("state", UNSET))

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

        def _parse_duration_ms(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        duration_ms = _parse_duration_ms(d.pop("durationMs", UNSET))

        def _parse_artwork_url(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        artwork_url = _parse_artwork_url(d.pop("artworkUrl", UNSET))

        def _parse_progress(data: object) -> float | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(float | None | Unset, data)

        progress = _parse_progress(d.pop("progress", UNSET))

        def _parse_elapsed_ms(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        elapsed_ms = _parse_elapsed_ms(d.pop("elapsedMs", UNSET))

        def _parse_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        id = _parse_id(d.pop("id", UNSET))

        overlay_now_playing = cls(
            is_playing=is_playing,
            state=state,
            title=title,
            artist=artist,
            album=album,
            duration_ms=duration_ms,
            artwork_url=artwork_url,
            progress=progress,
            elapsed_ms=elapsed_ms,
            id=id,
        )

        overlay_now_playing.additional_properties = d
        return overlay_now_playing

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
