from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.smartlist_create_rules_item import SmartlistCreateRulesItem


T = TypeVar("T", bound="SmartlistCreate")


@_attrs_define
class SmartlistCreate:
    """
    Attributes:
        name (str):
        description (None | str | Unset):  Default: ''.
        rules (list[SmartlistCreateRulesItem] | Unset):
        sort (None | str | Unset):
        limit (int | None | Unset):
        refresh_s (int | None | Unset):
    """

    name: str
    description: None | str | Unset = ""
    rules: list[SmartlistCreateRulesItem] | Unset = UNSET
    sort: None | str | Unset = UNSET
    limit: int | None | Unset = UNSET
    refresh_s: int | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        description: None | str | Unset
        if isinstance(self.description, Unset):
            description = UNSET
        else:
            description = self.description

        rules: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.rules, Unset):
            rules = []
            for rules_item_data in self.rules:
                rules_item = rules_item_data.to_dict()
                rules.append(rules_item)

        sort: None | str | Unset
        if isinstance(self.sort, Unset):
            sort = UNSET
        else:
            sort = self.sort

        limit: int | None | Unset
        if isinstance(self.limit, Unset):
            limit = UNSET
        else:
            limit = self.limit

        refresh_s: int | None | Unset
        if isinstance(self.refresh_s, Unset):
            refresh_s = UNSET
        else:
            refresh_s = self.refresh_s

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
            }
        )
        if description is not UNSET:
            field_dict["description"] = description
        if rules is not UNSET:
            field_dict["rules"] = rules
        if sort is not UNSET:
            field_dict["sort"] = sort
        if limit is not UNSET:
            field_dict["limit"] = limit
        if refresh_s is not UNSET:
            field_dict["refresh_s"] = refresh_s

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.smartlist_create_rules_item import SmartlistCreateRulesItem  # noqa: PLC0415

        d = dict(src_dict)
        name = d.pop("name")

        def _parse_description(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        description = _parse_description(d.pop("description", UNSET))

        _rules = d.pop("rules", UNSET)
        rules: list[SmartlistCreateRulesItem] | Unset = UNSET
        if _rules is not UNSET:
            rules = []
            for rules_item_data in _rules:
                rules_item = SmartlistCreateRulesItem.from_dict(rules_item_data)

                rules.append(rules_item)

        def _parse_sort(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        sort = _parse_sort(d.pop("sort", UNSET))

        def _parse_limit(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        limit = _parse_limit(d.pop("limit", UNSET))

        def _parse_refresh_s(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        refresh_s = _parse_refresh_s(d.pop("refresh_s", UNSET))

        smartlist_create = cls(
            name=name,
            description=description,
            rules=rules,
            sort=sort,
            limit=limit,
            refresh_s=refresh_s,
        )

        smartlist_create.additional_properties = d
        return smartlist_create

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
