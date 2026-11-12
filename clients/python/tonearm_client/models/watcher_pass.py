from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="WatcherPass")


@_attrs_define
class WatcherPass:
    """
    Attributes:
        ran (bool | Unset):  Default: True.
        artists_seen (int | Unset):  Default: 0.
        checked (int | Unset):  Default: 0.
        mapped (int | Unset):  Default: 0.
        unmapped (int | Unset):  Default: 0.
        new_releases (int | Unset):  Default: 0.
        auto_added (int | Unset):  Default: 0.
        skipped_budget (bool | None | Unset):
        seconds (float | None | Unset):
        completed_at (float | None | Unset):
    """

    ran: bool | Unset = True
    artists_seen: int | Unset = 0
    checked: int | Unset = 0
    mapped: int | Unset = 0
    unmapped: int | Unset = 0
    new_releases: int | Unset = 0
    auto_added: int | Unset = 0
    skipped_budget: bool | None | Unset = UNSET
    seconds: float | None | Unset = UNSET
    completed_at: float | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        ran = self.ran

        artists_seen = self.artists_seen

        checked = self.checked

        mapped = self.mapped

        unmapped = self.unmapped

        new_releases = self.new_releases

        auto_added = self.auto_added

        skipped_budget: bool | None | Unset
        if isinstance(self.skipped_budget, Unset):
            skipped_budget = UNSET
        else:
            skipped_budget = self.skipped_budget

        seconds: float | None | Unset
        if isinstance(self.seconds, Unset):
            seconds = UNSET
        else:
            seconds = self.seconds

        completed_at: float | None | Unset
        if isinstance(self.completed_at, Unset):
            completed_at = UNSET
        else:
            completed_at = self.completed_at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if ran is not UNSET:
            field_dict["ran"] = ran
        if artists_seen is not UNSET:
            field_dict["artists_seen"] = artists_seen
        if checked is not UNSET:
            field_dict["checked"] = checked
        if mapped is not UNSET:
            field_dict["mapped"] = mapped
        if unmapped is not UNSET:
            field_dict["unmapped"] = unmapped
        if new_releases is not UNSET:
            field_dict["new_releases"] = new_releases
        if auto_added is not UNSET:
            field_dict["auto_added"] = auto_added
        if skipped_budget is not UNSET:
            field_dict["skipped_budget"] = skipped_budget
        if seconds is not UNSET:
            field_dict["seconds"] = seconds
        if completed_at is not UNSET:
            field_dict["completed_at"] = completed_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        ran = d.pop("ran", UNSET)

        artists_seen = d.pop("artists_seen", UNSET)

        checked = d.pop("checked", UNSET)

        mapped = d.pop("mapped", UNSET)

        unmapped = d.pop("unmapped", UNSET)

        new_releases = d.pop("new_releases", UNSET)

        auto_added = d.pop("auto_added", UNSET)

        def _parse_skipped_budget(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        skipped_budget = _parse_skipped_budget(d.pop("skipped_budget", UNSET))

        def _parse_seconds(data: object) -> float | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(float | None | Unset, data)

        seconds = _parse_seconds(d.pop("seconds", UNSET))

        def _parse_completed_at(data: object) -> float | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(float | None | Unset, data)

        completed_at = _parse_completed_at(d.pop("completed_at", UNSET))

        watcher_pass = cls(
            ran=ran,
            artists_seen=artists_seen,
            checked=checked,
            mapped=mapped,
            unmapped=unmapped,
            new_releases=new_releases,
            auto_added=auto_added,
            skipped_budget=skipped_budget,
            seconds=seconds,
            completed_at=completed_at,
        )

        watcher_pass.additional_properties = d
        return watcher_pass

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
