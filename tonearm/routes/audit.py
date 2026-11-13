"""GET /api/audit — who did what (v0.7 #47). MASTER KEY ONLY: friends
don't audit each other; a scoped key asking gets 403 audit_forbidden."""
from fastapi import APIRouter, Request

from .. import audit
from ..errors import ApiError
from ..models import AuditExport

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=AuditExport)
def export(request: Request, since: float = 0.0, limit: int = 200,
           offset: int = 0):
    identity = getattr(request.state, "identity", None)
    if identity is None or not identity.is_master:
        raise ApiError(403, "audit_admin_only",
                       "the audit log is master-key only — scoped keys "
                       "don't audit each other")
    return audit.export(since=since, limit=limit, offset=offset)
