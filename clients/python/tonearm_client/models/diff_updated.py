from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define

if TYPE_CHECKING:
    from ..models.store_row_page import StoreRowPage


T = TypeVar("T", bound="DiffUpdated")


@_attrs_define
class DiffUpdated:
    """
    Attributes:
        updated (StoreRowPage):
    """

    updated: StoreRowPage

    def to_dict(self) -> dict[str, Any]:
        updated = self.updated.to_dict()

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "updated": updated,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.store_row_page import StoreRowPage  # noqa: PLC0415

        d = dict(src_dict)
        updated = StoreRowPage.from_dict(d.pop("updated"))

        diff_updated = cls(
            updated=updated,
        )

        return diff_updated
