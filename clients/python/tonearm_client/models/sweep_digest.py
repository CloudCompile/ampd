from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.item_row import ItemRow


T = TypeVar("T", bound="SweepDigest")


@_attrs_define
class SweepDigest:
    """
    Attributes:
        generated_at (str):
        library_size (int):
        duplicate_groups (int):
        removable_rows (int):
        never_played (int):
        play_count_available (bool):
        sample_duplicates (list[list[ItemRow]] | Unset):
        sample_never_played (list[ItemRow] | Unset):
    """

    generated_at: str
    library_size: int
    duplicate_groups: int
    removable_rows: int
    never_played: int
    play_count_available: bool
    sample_duplicates: list[list[ItemRow]] | Unset = UNSET
    sample_never_played: list[ItemRow] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        generated_at = self.generated_at

        library_size = self.library_size

        duplicate_groups = self.duplicate_groups

        removable_rows = self.removable_rows

        never_played = self.never_played

        play_count_available = self.play_count_available

        sample_duplicates: list[list[dict[str, Any]]] | Unset = UNSET
        if not isinstance(self.sample_duplicates, Unset):
            sample_duplicates = []
            for sample_duplicates_item_data in self.sample_duplicates:
                sample_duplicates_item = []
                for sample_duplicates_item_item_data in sample_duplicates_item_data:
                    sample_duplicates_item_item = sample_duplicates_item_item_data.to_dict()
                    sample_duplicates_item.append(sample_duplicates_item_item)

                sample_duplicates.append(sample_duplicates_item)

        sample_never_played: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.sample_never_played, Unset):
            sample_never_played = []
            for sample_never_played_item_data in self.sample_never_played:
                sample_never_played_item = sample_never_played_item_data.to_dict()
                sample_never_played.append(sample_never_played_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "generated_at": generated_at,
                "library_size": library_size,
                "duplicate_groups": duplicate_groups,
                "removable_rows": removable_rows,
                "never_played": never_played,
                "play_count_available": play_count_available,
            }
        )
        if sample_duplicates is not UNSET:
            field_dict["sample_duplicates"] = sample_duplicates
        if sample_never_played is not UNSET:
            field_dict["sample_never_played"] = sample_never_played

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.item_row import ItemRow  # noqa: PLC0415

        d = dict(src_dict)
        generated_at = d.pop("generated_at")

        library_size = d.pop("library_size")

        duplicate_groups = d.pop("duplicate_groups")

        removable_rows = d.pop("removable_rows")

        never_played = d.pop("never_played")

        play_count_available = d.pop("play_count_available")

        _sample_duplicates = d.pop("sample_duplicates", UNSET)
        sample_duplicates: list[list[ItemRow]] | Unset = UNSET
        if _sample_duplicates is not UNSET:
            sample_duplicates = []
            for sample_duplicates_item_data in _sample_duplicates:
                sample_duplicates_item = []
                _sample_duplicates_item = sample_duplicates_item_data
                for sample_duplicates_item_item_data in _sample_duplicates_item:
                    sample_duplicates_item_item = ItemRow.from_dict(sample_duplicates_item_item_data)

                    sample_duplicates_item.append(sample_duplicates_item_item)

                sample_duplicates.append(sample_duplicates_item)

        _sample_never_played = d.pop("sample_never_played", UNSET)
        sample_never_played: list[ItemRow] | Unset = UNSET
        if _sample_never_played is not UNSET:
            sample_never_played = []
            for sample_never_played_item_data in _sample_never_played:
                sample_never_played_item = ItemRow.from_dict(sample_never_played_item_data)

                sample_never_played.append(sample_never_played_item)

        sweep_digest = cls(
            generated_at=generated_at,
            library_size=library_size,
            duplicate_groups=duplicate_groups,
            removable_rows=removable_rows,
            never_played=never_played,
            play_count_available=play_count_available,
            sample_duplicates=sample_duplicates,
            sample_never_played=sample_never_played,
        )

        sweep_digest.additional_properties = d
        return sweep_digest

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
