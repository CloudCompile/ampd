from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define

if TYPE_CHECKING:
    from ..models.store_row_page import StoreRowPage


T = TypeVar("T", bound="DiffRemoved")


@_attrs_define
class DiffRemoved:
    """
    Attributes:
        removed (StoreRowPage):
    """

    removed: StoreRowPage

    def to_dict(self) -> dict[str, Any]:
        removed = self.removed.to_dict()

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "removed": removed,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.store_row_page import StoreRowPage  # noqa: PLC0415

        d = dict(src_dict)
        removed = StoreRowPage.from_dict(d.pop("removed"))

        diff_removed = cls(
            removed=removed,
        )

        return diff_removed
