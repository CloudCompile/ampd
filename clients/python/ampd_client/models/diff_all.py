from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.diff_all_walk_type_0 import DiffAllWalkType0
    from ..models.store_row_page import StoreRowPage


T = TypeVar("T", bound="DiffAll")


@_attrs_define
class DiffAll:
    """`what=all` (the default): all three pages + the last walk cursor.

    Attributes:
        added (StoreRowPage):
        updated (StoreRowPage):
        removed (StoreRowPage):
        walk (DiffAllWalkType0 | None | Unset):
    """

    added: StoreRowPage
    updated: StoreRowPage
    removed: StoreRowPage
    walk: DiffAllWalkType0 | None | Unset = UNSET

    def to_dict(self) -> dict[str, Any]:
        from ..models.diff_all_walk_type_0 import DiffAllWalkType0  # noqa: PLC0415

        added = self.added.to_dict()

        updated = self.updated.to_dict()

        removed = self.removed.to_dict()

        walk: dict[str, Any] | None | Unset
        if isinstance(self.walk, Unset):
            walk = UNSET
        elif isinstance(self.walk, DiffAllWalkType0):
            walk = self.walk.to_dict()
        else:
            walk = self.walk

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "added": added,
                "updated": updated,
                "removed": removed,
            }
        )
        if walk is not UNSET:
            field_dict["walk"] = walk

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.diff_all_walk_type_0 import DiffAllWalkType0  # noqa: PLC0415
        from ..models.store_row_page import StoreRowPage  # noqa: PLC0415

        d = dict(src_dict)
        added = StoreRowPage.from_dict(d.pop("added"))

        updated = StoreRowPage.from_dict(d.pop("updated"))

        removed = StoreRowPage.from_dict(d.pop("removed"))

        def _parse_walk(data: object) -> DiffAllWalkType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                walk_type_0 = DiffAllWalkType0.from_dict(data)

                return walk_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(DiffAllWalkType0 | None | Unset, data)

        walk = _parse_walk(d.pop("walk", UNSET))

        diff_all = cls(
            added=added,
            updated=updated,
            removed=removed,
            walk=walk,
        )

        return diff_all
