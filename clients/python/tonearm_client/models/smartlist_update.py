from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.smartlist_update_rules_type_0_item import SmartlistUpdateRulesType0Item


T = TypeVar("T", bound="SmartlistUpdate")


@_attrs_define
class SmartlistUpdate:
    """
    Attributes:
        name (None | str | Unset):
        description (None | str | Unset):
        rules (list[SmartlistUpdateRulesType0Item] | None | Unset):
        sort (None | str | Unset):
        limit (int | None | Unset):
        refresh_s (int | None | Unset):
    """

    name: None | str | Unset = UNSET
    description: None | str | Unset = UNSET
    rules: list[SmartlistUpdateRulesType0Item] | None | Unset = UNSET
    sort: None | str | Unset = UNSET
    limit: int | None | Unset = UNSET
    refresh_s: int | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name: None | str | Unset
        if isinstance(self.name, Unset):
            name = UNSET
        else:
            name = self.name

        description: None | str | Unset
        if isinstance(self.description, Unset):
            description = UNSET
        else:
            description = self.description

        rules: list[dict[str, Any]] | None | Unset
        if isinstance(self.rules, Unset):
            rules = UNSET
        elif isinstance(self.rules, list):
            rules = []
            for rules_type_0_item_data in self.rules:
                rules_type_0_item = rules_type_0_item_data.to_dict()
                rules.append(rules_type_0_item)

        else:
            rules = self.rules

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
        field_dict.update({})
        if name is not UNSET:
            field_dict["name"] = name
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
        from ..models.smartlist_update_rules_type_0_item import SmartlistUpdateRulesType0Item  # noqa: PLC0415

        d = dict(src_dict)

        def _parse_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        name = _parse_name(d.pop("name", UNSET))

        def _parse_description(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        description = _parse_description(d.pop("description", UNSET))

        def _parse_rules(data: object) -> list[SmartlistUpdateRulesType0Item] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                rules_type_0 = []
                _rules_type_0 = data
                for rules_type_0_item_data in _rules_type_0:
                    rules_type_0_item = SmartlistUpdateRulesType0Item.from_dict(rules_type_0_item_data)

                    rules_type_0.append(rules_type_0_item)

                return rules_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[SmartlistUpdateRulesType0Item] | None | Unset, data)

        rules = _parse_rules(d.pop("rules", UNSET))

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

        smartlist_update = cls(
            name=name,
            description=description,
            rules=rules,
            sort=sort,
            limit=limit,
            refresh_s=refresh_s,
        )

        smartlist_update.additional_properties = d
        return smartlist_update

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
