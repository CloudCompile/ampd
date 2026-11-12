from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.smartlist_rules_item import SmartlistRulesItem


T = TypeVar("T", bound="Smartlist")


@_attrs_define
class Smartlist:
    """
    Attributes:
        id (str):
        name (str):
        rules (list[SmartlistRulesItem]):
        description (None | str | Unset):
        sort (None | str | Unset):
        limit (int | Unset):  Default: 0.
        refresh_s (int | Unset):  Default: 0.
        playlist_id (None | str | Unset):
        last_eval (float | None | Unset):
        last_sync (float | None | Unset):
        last_count (int | None | Unset):
        created_at (float | None | Unset):
        updated_at (float | None | Unset):
    """

    id: str
    name: str
    rules: list[SmartlistRulesItem]
    description: None | str | Unset = UNSET
    sort: None | str | Unset = UNSET
    limit: int | Unset = 0
    refresh_s: int | Unset = 0
    playlist_id: None | str | Unset = UNSET
    last_eval: float | None | Unset = UNSET
    last_sync: float | None | Unset = UNSET
    last_count: int | None | Unset = UNSET
    created_at: float | None | Unset = UNSET
    updated_at: float | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        name = self.name

        rules = []
        for rules_item_data in self.rules:
            rules_item = rules_item_data.to_dict()
            rules.append(rules_item)

        description: None | str | Unset
        if isinstance(self.description, Unset):
            description = UNSET
        else:
            description = self.description

        sort: None | str | Unset
        if isinstance(self.sort, Unset):
            sort = UNSET
        else:
            sort = self.sort

        limit = self.limit

        refresh_s = self.refresh_s

        playlist_id: None | str | Unset
        if isinstance(self.playlist_id, Unset):
            playlist_id = UNSET
        else:
            playlist_id = self.playlist_id

        last_eval: float | None | Unset
        if isinstance(self.last_eval, Unset):
            last_eval = UNSET
        else:
            last_eval = self.last_eval

        last_sync: float | None | Unset
        if isinstance(self.last_sync, Unset):
            last_sync = UNSET
        else:
            last_sync = self.last_sync

        last_count: int | None | Unset
        if isinstance(self.last_count, Unset):
            last_count = UNSET
        else:
            last_count = self.last_count

        created_at: float | None | Unset
        if isinstance(self.created_at, Unset):
            created_at = UNSET
        else:
            created_at = self.created_at

        updated_at: float | None | Unset
        if isinstance(self.updated_at, Unset):
            updated_at = UNSET
        else:
            updated_at = self.updated_at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "name": name,
                "rules": rules,
            }
        )
        if description is not UNSET:
            field_dict["description"] = description
        if sort is not UNSET:
            field_dict["sort"] = sort
        if limit is not UNSET:
            field_dict["limit"] = limit
        if refresh_s is not UNSET:
            field_dict["refresh_s"] = refresh_s
        if playlist_id is not UNSET:
            field_dict["playlist_id"] = playlist_id
        if last_eval is not UNSET:
            field_dict["last_eval"] = last_eval
        if last_sync is not UNSET:
            field_dict["last_sync"] = last_sync
        if last_count is not UNSET:
            field_dict["last_count"] = last_count
        if created_at is not UNSET:
            field_dict["created_at"] = created_at
        if updated_at is not UNSET:
            field_dict["updated_at"] = updated_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.smartlist_rules_item import SmartlistRulesItem  # noqa: PLC0415

        d = dict(src_dict)
        id = d.pop("id")

        name = d.pop("name")

        rules = []
        _rules = d.pop("rules")
        for rules_item_data in _rules:
            rules_item = SmartlistRulesItem.from_dict(rules_item_data)

            rules.append(rules_item)

        def _parse_description(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        description = _parse_description(d.pop("description", UNSET))

        def _parse_sort(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        sort = _parse_sort(d.pop("sort", UNSET))

        limit = d.pop("limit", UNSET)

        refresh_s = d.pop("refresh_s", UNSET)

        def _parse_playlist_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        playlist_id = _parse_playlist_id(d.pop("playlist_id", UNSET))

        def _parse_last_eval(data: object) -> float | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(float | None | Unset, data)

        last_eval = _parse_last_eval(d.pop("last_eval", UNSET))

        def _parse_last_sync(data: object) -> float | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(float | None | Unset, data)

        last_sync = _parse_last_sync(d.pop("last_sync", UNSET))

        def _parse_last_count(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        last_count = _parse_last_count(d.pop("last_count", UNSET))

        def _parse_created_at(data: object) -> float | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(float | None | Unset, data)

        created_at = _parse_created_at(d.pop("created_at", UNSET))

        def _parse_updated_at(data: object) -> float | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(float | None | Unset, data)

        updated_at = _parse_updated_at(d.pop("updated_at", UNSET))

        smartlist = cls(
            id=id,
            name=name,
            rules=rules,
            description=description,
            sort=sort,
            limit=limit,
            refresh_s=refresh_s,
            playlist_id=playlist_id,
            last_eval=last_eval,
            last_sync=last_sync,
            last_count=last_count,
            created_at=created_at,
            updated_at=updated_at,
        )

        smartlist.additional_properties = d
        return smartlist

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
