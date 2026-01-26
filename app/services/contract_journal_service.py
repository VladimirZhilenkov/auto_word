"""
Service for managing contract journal entries and generating contract documents.
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from docxtpl import DocxTemplate
from sqlalchemy import and_, func

from ..database.connection import DatabaseSession
from ..database.models import ContractJournal, Listener, Program
from .declension import get_declension_service


def _get_app_dir() -> Path:
    """Return application root directory (works for frozen builds)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent.parent


class ContractJournalService:
    """Service layer for ContractJournal with document generation helpers."""

    DEFAULT_TEMPLATE = "contract_template.docx"
    CONTRACTS_TEMPLATES_SUBDIR = "contracts"

    def __init__(self, templates_dir: Optional[Path] = None, output_dir: Optional[Path] = None):
        app_dir = _get_app_dir()
        base_templates = Path(templates_dir) if templates_dir else app_dir / "templates"
        self.templates_dir = base_templates / self.CONTRACTS_TEMPLATES_SUBDIR
        self.output_dir = Path(output_dir) if output_dir else app_dir / "docx_files" / "contracts"
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.declension = get_declension_service()

    def get_available_templates(self) -> List[str]:
        """Return list of available contract template files."""
        if not self.templates_dir.exists():
            return []
        templates = []
        for pattern in ["*.docx", "*.DOCX"]:
            templates.extend(self.templates_dir.glob(pattern))
        return sorted([t.name for t in templates if not t.name.startswith(("~$", "._"))])

    # ------------------------------------------------------------------
    # Core CRUD
    # ------------------------------------------------------------------
    def get_next_contract_number(self) -> int:
        with DatabaseSession() as session:
            max_num = session.query(func.max(ContractJournal.contract_number)).scalar()
            return int(max_num or 0) + 1

    def _get_next_in_session(self, session) -> int:
        max_num = session.query(func.max(ContractJournal.contract_number)).scalar()
        return int(max_num or 0) + 1

    def create_contract(
        self,
        listener_id: int,
        program_id: Optional[int],
        contract_date: date,
        **kwargs,
    ) -> int:
        with DatabaseSession() as session:
            return self._create_contract_in_session(session, listener_id, program_id, contract_date, **kwargs)

    def _create_contract_in_session(self, session, listener_id: int, program_id: Optional[int], contract_date: date, **kwargs) -> int:
        contract_number = kwargs.get("contract_number")
        if contract_number is None:
            contract_number = self._get_next_in_session(session)
        else:
            exists = session.query(ContractJournal).filter(
                ContractJournal.contract_number == contract_number
            ).first()
            if exists:
                raise ValueError(f"Договор с номером {contract_number} уже существует")

        listener = session.query(Listener).get(listener_id)
        program = session.query(Program).get(program_id) if program_id else None
        if not listener:
            raise ValueError("Слушатель не найден")

        listener_full_name = listener.full_name
        program_name = None
        if program:
            program_name = program.program_short_name or program.program_name

        entry = ContractJournal(
            contract_number=contract_number,
            contract_date=contract_date,
            listener_id=listener_id,
            program_id=program_id,
            listener_full_name=listener_full_name,
            program_name=program_name,
            contract_sum=kwargs.get("contract_sum"),
            payment_type=kwargs.get("payment_type"),
            notes=kwargs.get("notes"),
            document_path=kwargs.get("document_path"),
        )
        session.add(entry)
        return contract_number

    def create_contracts_batch(
        self,
        listener_ids: List[int],
        program_id: Optional[int],
        contract_date: date,
        template_name: Optional[str] = None,
        **kwargs,
    ) -> List[int]:
        created_numbers: List[int] = []
        with DatabaseSession() as session:
            program = session.query(Program).get(program_id) if program_id else None
            next_number = self._get_next_in_session(session)

            for offset, listener_id in enumerate(listener_ids):
                listener = session.query(Listener).get(listener_id)
                if not listener:
                    continue

                current_number = next_number + offset
                document_path = self._render_contract_document(
                    listener=listener,
                    program=program,
                    contract_number=current_number,
                    contract_date=contract_date,
                    template_name=template_name,
                    extra_context=kwargs.get("context") or {},
                )

                entry = ContractJournal(
                    contract_number=current_number,
                    contract_date=contract_date,
                    listener_id=listener.id,
                    program_id=program.id if program else None,
                    listener_full_name=listener.full_name,
                    program_name=program.program_short_name or program.program_name if program else None,
                    contract_sum=kwargs.get("contract_sum"),
                    payment_type=kwargs.get("payment_type"),
                    notes=kwargs.get("notes"),
                    document_path=document_path,
                )
                session.add(entry)
                created_numbers.append(current_number)

        return created_numbers

    def get_contracts(
        self,
        program_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        with DatabaseSession() as session:
            query = session.query(ContractJournal)
            if program_id:
                query = query.filter(ContractJournal.program_id == program_id)
            if start_date:
                query = query.filter(ContractJournal.contract_date >= start_date)
            if end_date:
                query = query.filter(ContractJournal.contract_date <= end_date)

            query = query.order_by(ContractJournal.contract_number.desc())
            rows = query.all()

            items: List[Dict[str, Any]] = []
            for r in rows:
                items.append(
                    {
                        "id": r.id,
                        "contract_number": r.contract_number,
                        "contract_date": r.contract_date,
                        "listener_full_name": r.listener_full_name,
                        "program_name": r.program_name,
                        "contract_sum": r.contract_sum,
                        "payment_type": r.payment_type,
                        "notes": r.notes,
                        "document_path": r.document_path,
                        "listener_id": r.listener_id,
                        "program_id": r.program_id,
                        "created_at": r.created_at,
                    }
                )

            if search:
                s = search.strip().lower()
                items = [
                    i
                    for i in items
                    if s in str(i.get("contract_number", "")).lower()
                    or s in (i.get("listener_full_name") or "").lower()
                    or s in (i.get("program_name") or "").lower()
                    or s in (i.get("notes") or "").lower()
                ]

            return items

    def update_contract(self, contract_id: int, **kwargs) -> bool:
        allowed = {
            "contract_number",
            "contract_date",
            "listener_id",
            "program_id",
            "listener_full_name",
            "program_name",
            "contract_sum",
            "payment_type",
            "notes",
            "document_path",
        }
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return False

        with DatabaseSession() as session:
            entry: ContractJournal = session.query(ContractJournal).get(contract_id)
            if not entry:
                return False

            new_number = fields.get("contract_number", entry.contract_number)
            if new_number != entry.contract_number:
                exists = session.query(ContractJournal).filter(
                    and_(ContractJournal.contract_number == new_number, ContractJournal.id != contract_id)
                ).first()
                if exists:
                    raise ValueError(f"Договор с номером {new_number} уже существует")

            if "listener_id" in fields:
                listener = session.query(Listener).get(fields["listener_id"])
                if listener:
                    fields.setdefault("listener_full_name", listener.full_name)
            if "program_id" in fields:
                program = session.query(Program).get(fields["program_id"])
                if program:
                    fields.setdefault("program_name", program.program_short_name or program.program_name)

            for k, v in fields.items():
                setattr(entry, k, v)
            return True

    def delete_contract(self, contract_id: int) -> bool:
        with DatabaseSession() as session:
            entry = session.query(ContractJournal).get(contract_id)
            if not entry:
                return False
            session.delete(entry)
            return True

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------
    def export_to_excel(self, output_path: str, filters: Dict[str, Any]) -> bool:
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Alignment, Font
            from openpyxl.utils import get_column_letter

            entries = self.get_contracts(
                program_id=filters.get("program_id"),
                start_date=filters.get("start_date"),
                end_date=filters.get("end_date"),
                search=filters.get("search"),
            )
            if not entries:
                return False

            wb = Workbook()
            ws = wb.active
            ws.title = "Журнал договоров"

            headers = [
                "№ договора",
                "Дата",
                "ФИО слушателя",
                "Программа",
                "Сумма",
                "Тип оплаты",
                "Примечания",
            ]
            ws.append(headers)

            for idx in range(1, len(headers) + 1):
                cell = ws.cell(row=1, column=idx)
                cell.font = Font(bold=True)
                cell.alignment = Alignment(horizontal="center")

            for item in entries:
                ws.append(
                    [
                        item.get("contract_number"),
                        item.get("contract_date").strftime("%d.%m.%Y") if item.get("contract_date") else "",
                        item.get("listener_full_name") or "",
                        item.get("program_name") or "",
                        item.get("contract_sum") or "",
                        item.get("payment_type") or "",
                        item.get("notes") or "",
                    ]
                )

            widths = [12, 12, 32, 32, 12, 14, 40]
            for i, w in enumerate(widths, start=1):
                ws.column_dimensions[get_column_letter(i)].width = w

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            wb.save(output_path)
            return True
        except Exception as exc:
            print(f"Excel export failed: {exc}")
            return False

    # ------------------------------------------------------------------
    # Document rendering
    # ------------------------------------------------------------------
    def _render_contract_document(
        self,
        listener: Listener,
        program: Optional[Program],
        contract_number: int,
        contract_date: date,
        template_name: Optional[str] = None,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        tpl_name = template_name or self.DEFAULT_TEMPLATE
        template_path = self.templates_dir / tpl_name
        if not template_path.exists():
            return None

        context = self._build_context(listener, program, contract_number, contract_date)
        if extra_context:
            context.update(extra_context)

        try:
            doc = DocxTemplate(template_path)
            doc.render(context)
            safe_name = listener.full_name.replace(" ", "_")
            filename = f"Договор_{contract_number:03d}_{safe_name}.docx"
            output_path = self.output_dir / filename
            doc.save(output_path)
            return str(output_path)
        except Exception as exc:
            print(f"Contract render failed: {exc}")
            return None

    def _build_context(
        self,
        listener: Listener,
        program: Optional[Program],
        contract_number: int,
        contract_date: date,
    ) -> Dict[str, Any]:
        ctx: Dict[str, Any] = {
            "contract_number": contract_number,
            "contract_date": contract_date.strftime("%d.%m.%Y"),
            "listener_full_name": listener.full_name,
            "listener_passport": listener.passport_series_number or "",
            "listener_address": listener.registration_address or "",
            "listener_phone": listener.mobile_phone or "",
            "listener_email": listener.email or "",
        }

        decl = self.declension.get_all_declensions(
            listener.last_name or "",
            listener.first_name or "",
            listener.middle_name,
        )
        ctx["listener_full_name_genitive"] = decl.get("full_name_genitive", "")
        ctx.update(decl)

        if program:
            ctx.update(
                {
                    "program_name": program.program_name or "",
                    "program_volume": program.program_volume or "",
                    "training_period": program.training_period or "",
                }
            )
        else:
            ctx.update({"program_name": "", "program_volume": "", "training_period": ""})

        return ctx

