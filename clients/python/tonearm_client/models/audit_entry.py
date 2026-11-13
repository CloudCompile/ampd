from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="AuditEntry")


@_attrs_define
class AuditEntry:
    """
    Attributes:
        ts (float):
        key_id (str):
        method (str):
        path (str):
        status (int):
    """

    ts: float
    key_id: str
    method: str
    path: str
    status: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        ts = self.ts

        key_id = self.key_id

        method = self.method

        path = self.path

        status = self.status

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "ts": ts,
                "key_id": key_id,
                "method": method,
                "path": path,
                "status": status,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        ts = d.pop("ts")

        key_id = d.pop("key_id")

        method = d.pop("method")

        path = d.pop("path")

        status = d.pop("status")

        audit_entry = cls(
            ts=ts,
            key_id=key_id,
            method=method,
            path=path,
            status=status,
        )

        audit_entry.additional_properties = d
        return audit_entry

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
