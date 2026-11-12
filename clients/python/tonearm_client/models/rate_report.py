from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.write_error import WriteError


T = TypeVar("T", bound="RateReport")


@_attrs_define
class RateReport:
    """
    Attributes:
        ok (bool):
        hearted (list[str]):
        already_hearted (list[str]):
        errors (list[WriteError]):
        hearted_count (int):
    """

    ok: bool
    hearted: list[str]
    already_hearted: list[str]
    errors: list[WriteError]
    hearted_count: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        ok = self.ok

        hearted = self.hearted

        already_hearted = self.already_hearted

        errors = []
        for errors_item_data in self.errors:
            errors_item = errors_item_data.to_dict()
            errors.append(errors_item)

        hearted_count = self.hearted_count

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "ok": ok,
                "hearted": hearted,
                "already_hearted": already_hearted,
                "errors": errors,
                "hearted_count": hearted_count,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.write_error import WriteError  # noqa: PLC0415

        d = dict(src_dict)
        ok = d.pop("ok")

        hearted = cast(list[str], d.pop("hearted"))

        already_hearted = cast(list[str], d.pop("already_hearted"))

        errors = []
        _errors = d.pop("errors")
        for errors_item_data in _errors:
            errors_item = WriteError.from_dict(errors_item_data)

            errors.append(errors_item)

        hearted_count = d.pop("hearted_count")

        rate_report = cls(
            ok=ok,
            hearted=hearted,
            already_hearted=already_hearted,
            errors=errors,
            hearted_count=hearted_count,
        )

        rate_report.additional_properties = d
        return rate_report

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
