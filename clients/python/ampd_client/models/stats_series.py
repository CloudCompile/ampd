from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.series_point import SeriesPoint


T = TypeVar("T", bound="StatsSeries")


@_attrs_define
class StatsSeries:
    """
    Attributes:
        days (int):
        series (list[SeriesPoint]):
    """

    days: int
    series: list[SeriesPoint]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        days = self.days

        series = []
        for series_item_data in self.series:
            series_item = series_item_data.to_dict()
            series.append(series_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "days": days,
                "series": series,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.series_point import SeriesPoint  # noqa: PLC0415

        d = dict(src_dict)
        days = d.pop("days")

        series = []
        _series = d.pop("series")
        for series_item_data in _series:
            series_item = SeriesPoint.from_dict(series_item_data)

            series.append(series_item)

        stats_series = cls(
            days=days,
            series=series,
        )

        stats_series.additional_properties = d
        return stats_series

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
