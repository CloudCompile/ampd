from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.write_error import WriteError


T = TypeVar("T", bound="DedupeReport")


@_attrs_define
class DedupeReport:
    """
    Attributes:
        ok (bool):
        removed (list[str]):
        errors (list[WriteError]):
        removed_count (int):
    """

    ok: bool
    removed: list[str]
    errors: list[WriteError]
    removed_count: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        ok = self.ok

        removed = self.removed

        errors = []
        for errors_item_data in self.errors:
            errors_item = errors_item_data.to_dict()
            errors.append(errors_item)

        removed_count = self.removed_count

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "ok": ok,
                "removed": removed,
                "errors": errors,
                "removed_count": removed_count,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.write_error import WriteError  # noqa: PLC0415

        d = dict(src_dict)
        ok = d.pop("ok")

        removed = cast(list[str], d.pop("removed"))

        errors = []
        _errors = d.pop("errors")
        for errors_item_data in _errors:
            errors_item = WriteError.from_dict(errors_item_data)

            errors.append(errors_item)

        removed_count = d.pop("removed_count")

        dedupe_report = cls(
            ok=ok,
            removed=removed,
            errors=errors,
            removed_count=removed_count,
        )

        dedupe_report.additional_properties = d
        return dedupe_report

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
