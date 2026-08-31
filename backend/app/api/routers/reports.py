import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.api.routers.audits import get_audit_or_404
from app.core.permissions import Permission
from app.models.entitlement import EntitlementGroup, EntitlementItem
from app.models.enums import Classification, ExcessStatus, MatchStatus
from app.models.finding import Finding
from app.models.import_transaction import ImportTransaction
from app.models.report import GeneratedReport
from app.models.user import User
from app.services import storage
from app.services.exception_queries import compute_exceptions
from app.services.reporting_engine import (
    ExceptionSummary,
    ReportEntitlementItem,
    ReportFindingLine,
    ReportTransactionLine,
    generate_output_01,
    generate_output_02,
    generate_output_03,
    generate_output_04,
    generate_output_05,
    generate_output_06,
    generate_output_07,
)

router = APIRouter(prefix="/api/audits/{audit_id}/reports", tags=["reports"])

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _report_items(db: Session, audit_id: str) -> list[ReportEntitlementItem]:
    rows = (
        db.query(EntitlementItem)
        .join(EntitlementGroup, EntitlementItem.group_id == EntitlementGroup.id)
        .filter(EntitlementGroup.audit_id == audit_id)
        .order_by(EntitlementGroup.sequence_no, EntitlementItem.sequence_no)
        .all()
    )
    return [
        ReportEntitlementItem(
            entitlement_item_id=i.id,
            group_sequence_no=i.group.sequence_no,
            group_name=i.group.group_name,
            item_sequence_no=i.sequence_no,
            material_name=i.material_name,
            hs_code=i.hs_code,
            entitlement_unit=i.entitlement_unit,
            annual_entitlement_qty=i.annual_entitlement_qty,
            enhanced_entitlement_qty=i.enhanced_entitlement_qty,
            total_entitlement_qty=i.total_entitlement_qty,
        )
        for i in rows
    ]


def _to_transaction_line(t: ImportTransaction) -> ReportTransactionLine:
    return ReportTransactionLine(
        entitlement_item_id=t.entitlement_item_id,
        material_name=t.item_description,
        hs_code=t.hs_code,
        be_number=t.be_number,
        be_date=t.be_date,
        declared_quantity=t.declared_quantity,
        declared_unit=t.declared_unit,
        entitlement_quantity=t.entitlement_quantity,
        entitlement_unit=t.entitlement_unit,
        kg_quantity=t.kg_quantity,
        original_currency=t.original_currency,
        original_currency_value=t.original_currency_value,
        usd_value=t.usd_value,
        classification=t.classification,
    )


def _lines_by_item(db: Session, audit_id: str) -> dict[str, list[ReportTransactionLine]]:
    rows = (
        db.query(ImportTransaction)
        .filter(
            ImportTransaction.audit_id == audit_id,
            ImportTransaction.classification == Classification.RAW_MATERIAL,
            ImportTransaction.match_status == MatchStatus.APPROVED,
        )
        .order_by(ImportTransaction.be_date, ImportTransaction.be_number)
        .all()
    )
    grouped: dict[str, list[ReportTransactionLine]] = {}
    for t in rows:
        if not t.entitlement_item_id:
            continue
        grouped.setdefault(t.entitlement_item_id, []).append(_to_transaction_line(t))
    return grouped


def _to_finding_line(f: Finding) -> ReportFindingLine:
    return ReportFindingLine(
        finding_code=f.finding_code,
        issue_type=f.issue_type,
        evidence=f.evidence,
        be_number=f.import_transaction.be_number if f.import_transaction else None,
        material_name=f.material_name,
        quantity=f.quantity,
        unit=f.unit,
        value=f.value,
        demand_amount=f.demand_amount,
        review_status=f.review_status,
    )


def _persist_and_stream(db: Session, audit_id: str, output_code: str, workbook, current_user: User) -> StreamingResponse:
    buffer = io.BytesIO()
    workbook.save(buffer)
    content = buffer.getvalue()

    backend = storage.get_storage_backend()
    checksum = storage.sha256_checksum(content)
    key = storage.build_storage_key(audit_id, checksum, f"{output_code}.xlsx")
    backend.write(key, content)

    db.add(GeneratedReport(audit_id=audit_id, output_code=output_code, storage_key=key, generated_by=current_user.id))
    db.commit()

    return StreamingResponse(
        io.BytesIO(content),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{output_code}.xlsx"'},
    )


@router.post("/output-01")
def report_output_01(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.GENERATE_REPORTS)),
) -> StreamingResponse:
    audit = get_audit_or_404(db, audit_id)
    workbook = generate_output_01(_report_items(db, audit_id), _lines_by_item(db, audit_id), audit.title)
    return _persist_and_stream(db, audit_id, "OUTPUT_01", workbook, current_user)


@router.post("/output-02")
def report_output_02(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.GENERATE_REPORTS)),
) -> StreamingResponse:
    audit = get_audit_or_404(db, audit_id)
    workbook = generate_output_02(_report_items(db, audit_id), _lines_by_item(db, audit_id), audit.title)
    return _persist_and_stream(db, audit_id, "OUTPUT_02", workbook, current_user)


@router.post("/output-03")
def report_output_03(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.GENERATE_REPORTS)),
) -> StreamingResponse:
    audit = get_audit_or_404(db, audit_id)
    machinery = [
        _to_transaction_line(t)
        for t in db.query(ImportTransaction)
        .filter(ImportTransaction.audit_id == audit_id, ImportTransaction.classification == Classification.MACHINERY)
        .order_by(ImportTransaction.be_date)
        .all()
    ]
    sample = [
        _to_transaction_line(t)
        for t in db.query(ImportTransaction)
        .filter(ImportTransaction.audit_id == audit_id, ImportTransaction.classification == Classification.SAMPLE)
        .order_by(ImportTransaction.be_date)
        .all()
    ]
    workbook = generate_output_03(machinery, sample, audit.title)
    return _persist_and_stream(db, audit_id, "OUTPUT_03", workbook, current_user)


@router.post("/output-04")
def report_output_04(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.GENERATE_REPORTS)),
) -> StreamingResponse:
    audit = get_audit_or_404(db, audit_id)
    data = compute_exceptions(db, audit_id)

    summary = ExceptionSummary(
        non_entitled_count=len(data.non_entitled),
        review_required_match_count=len(data.review_required),
        unknown_classification_count=len(data.unknown_classification),
        partial_excess_count=len([t for t in data.excess if t.excess_status == ExcessStatus.PARTIAL_EXCESS]),
        full_excess_count=len([t for t in data.excess if t.excess_status == ExcessStatus.FULL_EXCESS]),
        conversion_incomplete_count=len(data.conversion_incomplete),
    )
    workbook = generate_output_04(summary, audit.title)
    return _persist_and_stream(db, audit_id, "OUTPUT_04", workbook, current_user)


def _findings(db: Session, audit_id: str, issue_types: tuple[str, ...] | None = None) -> list[ReportFindingLine]:
    query = db.query(Finding).filter(Finding.audit_id == audit_id)
    if issue_types:
        query = query.filter(Finding.issue_type.in_(issue_types))
    rows = query.order_by(Finding.finding_code).all()
    return [_to_finding_line(f) for f in rows]


@router.post("/output-05")
def report_output_05(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.GENERATE_REPORTS)),
) -> StreamingResponse:
    audit = get_audit_or_404(db, audit_id)
    workbook = generate_output_05(_findings(db, audit_id, ("non_entitled",)), audit.title)
    return _persist_and_stream(db, audit_id, "OUTPUT_05", workbook, current_user)


@router.post("/output-06")
def report_output_06(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.GENERATE_REPORTS)),
) -> StreamingResponse:
    audit = get_audit_or_404(db, audit_id)
    workbook = generate_output_06(_findings(db, audit_id, ("excess_partial", "excess_full")), audit.title)
    return _persist_and_stream(db, audit_id, "OUTPUT_06", workbook, current_user)


@router.post("/output-07")
def report_output_07(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.GENERATE_REPORTS)),
) -> StreamingResponse:
    audit = get_audit_or_404(db, audit_id)
    workbook = generate_output_07(_findings(db, audit_id), audit.title)
    return _persist_and_stream(db, audit_id, "OUTPUT_07", workbook, current_user)


@router.get("/history")
def report_history(
    audit_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> list[dict]:
    """Spec section 19: generated reports record their source audit ID and generation time."""
    get_audit_or_404(db, audit_id)
    rows = db.query(GeneratedReport).filter(GeneratedReport.audit_id == audit_id).order_by(GeneratedReport.generated_at.desc()).all()
    return [
        {
            "id": r.id,
            "output_code": r.output_code,
            "generated_by": r.generated_by,
            "generated_at": r.generated_at.isoformat(),
        }
        for r in rows
    ]
