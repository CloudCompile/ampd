from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define

if TYPE_CHECKING:
    from ..models.store_row_page import StoreRowPage


T = TypeVar("T", bound="DiffAdded")


@_attrs_define
class DiffAdded:
    """
    Attributes:
        added (StoreRowPage):
    """

    added: StoreRowPage

    def to_dict(self) -> dict[str, Any]:
        added = self.added.to_dict()

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "added": added,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.store_row_page import StoreRowPage  # noqa: PLC0415

        d = dict(src_dict)
        added = StoreRowPage.from_dict(d.pop("added"))

        diff_added = cls(
            added=added,
        )

        return diff_added
