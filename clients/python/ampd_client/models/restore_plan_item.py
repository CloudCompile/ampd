from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.restore_plan_item_actions_item import RestorePlanItemActionsItem
    from ..models.restore_plan_item_unmatched_item import RestorePlanItemUnmatchedItem


T = TypeVar("T", bound="RestorePlanItem")


@_attrs_define
class RestorePlanItem:
    """
    Attributes:
        name (str):
        mode (str):
        track_count (int):
        actions (list[RestorePlanItemActionsItem]):
        unmatched (list[RestorePlanItemUnmatchedItem]):
        playlist_id (None | str | Unset):
    """

    name: str
    mode: str
    track_count: int
    actions: list[RestorePlanItemActionsItem]
    unmatched: list[RestorePlanItemUnmatchedItem]
    playlist_id: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        mode = self.mode

        track_count = self.track_count

        actions = []
        for actions_item_data in self.actions:
            actions_item = actions_item_data.to_dict()
            actions.append(actions_item)

        unmatched = []
        for unmatched_item_data in self.unmatched:
            unmatched_item = unmatched_item_data.to_dict()
            unmatched.append(unmatched_item)

        playlist_id: None | str | Unset
        if isinstance(self.playlist_id, Unset):
            playlist_id = UNSET
        else:
            playlist_id = self.playlist_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
                "mode": mode,
                "track_count": track_count,
                "actions": actions,
                "unmatched": unmatched,
            }
        )
        if playlist_id is not UNSET:
            field_dict["playlist_id"] = playlist_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.restore_plan_item_actions_item import RestorePlanItemActionsItem  # noqa: PLC0415
        from ..models.restore_plan_item_unmatched_item import RestorePlanItemUnmatchedItem  # noqa: PLC0415

        d = dict(src_dict)
        name = d.pop("name")

        mode = d.pop("mode")

        track_count = d.pop("track_count")

        actions = []
        _actions = d.pop("actions")
        for actions_item_data in _actions:
            actions_item = RestorePlanItemActionsItem.from_dict(actions_item_data)

            actions.append(actions_item)

        unmatched = []
        _unmatched = d.pop("unmatched")
        for unmatched_item_data in _unmatched:
            unmatched_item = RestorePlanItemUnmatchedItem.from_dict(unmatched_item_data)

            unmatched.append(unmatched_item)

        def _parse_playlist_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        playlist_id = _parse_playlist_id(d.pop("playlist_id", UNSET))

        restore_plan_item = cls(
            name=name,
            mode=mode,
            track_count=track_count,
            actions=actions,
            unmatched=unmatched,
            playlist_id=playlist_id,
        )

        restore_plan_item.additional_properties = d
        return restore_plan_item

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
