from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.restore_report_created_item import RestoreReportCreatedItem
    from ..models.restore_report_errors_item import RestoreReportErrorsItem
    from ..models.restore_report_mismatch_item import RestoreReportMismatchItem
    from ..models.restore_verified import RestoreVerified


T = TypeVar("T", bound="RestoreReport")


@_attrs_define
class RestoreReport:
    """
    Attributes:
        created (list[RestoreReportCreatedItem]):
        verified (list[RestoreVerified]):
        mismatch (list[RestoreReportMismatchItem]):
        errors (list[RestoreReportErrorsItem]):
        unmatched_total (int):
    """

    created: list[RestoreReportCreatedItem]
    verified: list[RestoreVerified]
    mismatch: list[RestoreReportMismatchItem]
    errors: list[RestoreReportErrorsItem]
    unmatched_total: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        created = []
        for created_item_data in self.created:
            created_item = created_item_data.to_dict()
            created.append(created_item)

        verified = []
        for verified_item_data in self.verified:
            verified_item = verified_item_data.to_dict()
            verified.append(verified_item)

        mismatch = []
        for mismatch_item_data in self.mismatch:
            mismatch_item = mismatch_item_data.to_dict()
            mismatch.append(mismatch_item)

        errors = []
        for errors_item_data in self.errors:
            errors_item = errors_item_data.to_dict()
            errors.append(errors_item)

        unmatched_total = self.unmatched_total

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "created": created,
                "verified": verified,
                "mismatch": mismatch,
                "errors": errors,
                "unmatched_total": unmatched_total,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.restore_report_created_item import RestoreReportCreatedItem  # noqa: PLC0415
        from ..models.restore_report_errors_item import RestoreReportErrorsItem  # noqa: PLC0415
        from ..models.restore_report_mismatch_item import RestoreReportMismatchItem  # noqa: PLC0415
        from ..models.restore_verified import RestoreVerified  # noqa: PLC0415

        d = dict(src_dict)
        created = []
        _created = d.pop("created")
        for created_item_data in _created:
            created_item = RestoreReportCreatedItem.from_dict(created_item_data)

            created.append(created_item)

        verified = []
        _verified = d.pop("verified")
        for verified_item_data in _verified:
            verified_item = RestoreVerified.from_dict(verified_item_data)

            verified.append(verified_item)

        mismatch = []
        _mismatch = d.pop("mismatch")
        for mismatch_item_data in _mismatch:
            mismatch_item = RestoreReportMismatchItem.from_dict(mismatch_item_data)

            mismatch.append(mismatch_item)

        errors = []
        _errors = d.pop("errors")
        for errors_item_data in _errors:
            errors_item = RestoreReportErrorsItem.from_dict(errors_item_data)

            errors.append(errors_item)

        unmatched_total = d.pop("unmatched_total")

        restore_report = cls(
            created=created,
            verified=verified,
            mismatch=mismatch,
            errors=errors,
            unmatched_total=unmatched_total,
        )

        restore_report.additional_properties = d
        return restore_report

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
