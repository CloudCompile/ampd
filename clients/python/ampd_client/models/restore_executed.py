from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.restore_executed_plan_totals import RestoreExecutedPlanTotals
    from ..models.restore_report import RestoreReport


T = TypeVar("T", bound="RestoreExecuted")


@_attrs_define
class RestoreExecuted:
    """
    Attributes:
        ok (bool):
        plan_totals (RestoreExecutedPlanTotals):
        report (RestoreReport):
    """

    ok: bool
    plan_totals: RestoreExecutedPlanTotals
    report: RestoreReport
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        ok = self.ok

        plan_totals = self.plan_totals.to_dict()

        report = self.report.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "ok": ok,
                "plan_totals": plan_totals,
                "report": report,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.restore_executed_plan_totals import RestoreExecutedPlanTotals  # noqa: PLC0415
        from ..models.restore_report import RestoreReport  # noqa: PLC0415

        d = dict(src_dict)
        ok = d.pop("ok")

        plan_totals = RestoreExecutedPlanTotals.from_dict(d.pop("plan_totals"))

        report = RestoreReport.from_dict(d.pop("report"))

        restore_executed = cls(
            ok=ok,
            plan_totals=plan_totals,
            report=report,
        )

        restore_executed.additional_properties = d
        return restore_executed

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
