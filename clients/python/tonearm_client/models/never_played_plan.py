from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.never_played_row import NeverPlayedRow


T = TypeVar("T", bound="NeverPlayedPlan")


@_attrs_define
class NeverPlayedPlan:
    """
    Attributes:
        library_size (int):
        never_played (int):
        play_count_available (bool):
        songs (list[NeverPlayedRow]):
    """

    library_size: int
    never_played: int
    play_count_available: bool
    songs: list[NeverPlayedRow]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        library_size = self.library_size

        never_played = self.never_played

        play_count_available = self.play_count_available

        songs = []
        for songs_item_data in self.songs:
            songs_item = songs_item_data.to_dict()
            songs.append(songs_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "library_size": library_size,
                "never_played": never_played,
                "play_count_available": play_count_available,
                "songs": songs,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.never_played_row import NeverPlayedRow  # noqa: PLC0415

        d = dict(src_dict)
        library_size = d.pop("library_size")

        never_played = d.pop("never_played")

        play_count_available = d.pop("play_count_available")

        songs = []
        _songs = d.pop("songs")
        for songs_item_data in _songs:
            songs_item = NeverPlayedRow.from_dict(songs_item_data)

            songs.append(songs_item)

        never_played_plan = cls(
            library_size=library_size,
            never_played=never_played,
            play_count_available=play_count_available,
            songs=songs,
        )

        never_played_plan.additional_properties = d
        return never_played_plan

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
