from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.restore_plan_item import RestorePlanItem
    from ..models.restore_plan_totals import RestorePlanTotals


T = TypeVar("T", bound="RestorePlan")


@_attrs_define
class RestorePlan:
    """
    Attributes:
        totals (RestorePlanTotals):
        playlists (list[RestorePlanItem]):
        note (None | str | Unset):
    """

    totals: RestorePlanTotals
    playlists: list[RestorePlanItem]
    note: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        totals = self.totals.to_dict()

        playlists = []
        for playlists_item_data in self.playlists:
            playlists_item = playlists_item_data.to_dict()
            playlists.append(playlists_item)

        note: None | str | Unset
        if isinstance(self.note, Unset):
            note = UNSET
        else:
            note = self.note

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "totals": totals,
                "playlists": playlists,
            }
        )
        if note is not UNSET:
            field_dict["note"] = note

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.restore_plan_item import RestorePlanItem  # noqa: PLC0415
        from ..models.restore_plan_totals import RestorePlanTotals  # noqa: PLC0415

        d = dict(src_dict)
        totals = RestorePlanTotals.from_dict(d.pop("totals"))

        playlists = []
        _playlists = d.pop("playlists")
        for playlists_item_data in _playlists:
            playlists_item = RestorePlanItem.from_dict(playlists_item_data)

            playlists.append(playlists_item)

        def _parse_note(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        note = _parse_note(d.pop("note", UNSET))

        restore_plan = cls(
            totals=totals,
            playlists=playlists,
            note=note,
        )

        restore_plan.additional_properties = d
        return restore_plan

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
