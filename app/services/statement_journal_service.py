"""
Service for managing Statement journals (Ведомости ИА, Ведомости ПА, Протоколы ИА).

Mirrors ContractJournalService but works with StatementJournal (kind-parameterized).
Supports per-kind numbering and document generation from templates.
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from docxtpl import DocxTemplate
from sqlalchemy import and_, func

from ..database.connection import DatabaseSession
from ..database.models import Listener, Program, StatementJournal
from .declension import get_declension_service


STATEMENT_KINDS: Dict[str, Dict[str, str]] = {
    'vedomost_ia': {
        'label': 'Ведомости ИА',
        'templates_subdir': 'vedomosti_ia',
        'output_subdir': 'vedomosti_ia',
        'doc_prefix': 'Ведомость_ИА',
    },
    'vedomost_pa': {
        'label': 'Ведомости ПА',
        'templates_subdir': 'vedomosti_pa',
        'output_subdir': 'vedomosti_pa',
        'doc_prefix': 'Ведомость_ПА',
    },
    'protokol_ia': {
        'label': 'Протоколы ИА',
        'templates_subdir': 'protokoly_ia',
        'output_subdir': 'protokoly_ia',
        'doc_prefix': 'Протокол_ИА',
    },
}


def _get_app_dir() -> Path:
    """Return application root directory (works for frozen builds)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent.parent


class StatementJournalService:
    """Service layer for StatementJournal (one instance per kind)."""

    def __init__(self, kind: str, templates_dir: Optional[Path] = None, output_dir: Optional[Path] = None):
        if kind not in STATEMENT_KINDS:
            raise ValueError(f"Unknown statement kind: {kind}")
        self.kind = kind
        self.config = STATEMENT_KINDS[kind]

        app_dir = _get_app_dir()
        base_templates = Path(templates_dir) if templates_dir else app_dir / "templates"
        self.templates_dir = base_templates / self.config['templates_subdir']
        self.output_dir = Path(output_dir) if output_dir else app_dir / "docx_files" / self.config['output_subdir']
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.declension = get_declension_service()

    # ------------------------------------------------------------------
    # Templates
    # ------------------------------------------------------------------
    def get_available_templates(self) -> List[str]:
        if not self.templates_dir.exists():
            return []
        seen: set = set()
        templates: List[str] = []
        for pattern in ("*.docx", "*.DOCX"):
            for t in self.templates_dir.glob(pattern):
                name = t.name
                key = name.lower()
                if key in seen:
                    continue
                if name.startswith(("~$", "._")):
                    continue
                seen.add(key)
                templates.append(name)
        return sorted(templates)

    # ------------------------------------------------------------------
    # Numbering
    # ------------------------------------------------------------------
    def get_next_number(self) -> int:
        with DatabaseSession() as session:
            max_num = session.query(func.max(StatementJournal.entry_number)).filter(
                StatementJournal.kind == self.kind
            ).scalar()
            return int(max_num or 0) + 1

    def _get_next_in_session(self, session) -> int:
        max_num = session.query(func.max(StatementJournal.entry_number)).filter(
            StatementJournal.kind == self.kind
        ).scalar()
        return int(max_num or 0) + 1

    # ------------------------------------------------------------------
    # CRUD + batch creation
    # ------------------------------------------------------------------
    def create_batch(
        self,
        listener_ids: List[int],
        program_id: Optional[int],
        entry_date: date,
        template_name: Optional[str] = None,
        notes: Optional[str] = None,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> List[int]:
        created: List[int] = []
        with DatabaseSession() as session:
            program = session.query(Program).get(program_id) if program_id else None
            next_num = self._get_next_in_session(session)

            for offset, lid in enumerate(listener_ids):
                listener = session.query(Listener).get(lid)
                if not listener:
                    continue
                number = next_num + offset
                doc_path = self._render_document(
                    listener=listener,
                    program=program,
                    entry_number=number,
                    entry_date=entry_date,
                    template_name=template_name,
                    extra_context=extra_context or {},
                )
                entry = StatementJournal(
                    kind=self.kind,
                    entry_number=number,
                    entry_date=entry_date,
                    listener_id=listener.id,
                    program_id=program.id if program else None,
                    listener_full_name=listener.full_name,
                    program_name=(program.program_name or program.program_short_name) if program else None,
                    notes=notes,
                    document_path=doc_path,
                )
                session.add(entry)
                created.append(number)
        return created

    def get_entries(
        self,
        program_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        with DatabaseSession() as session:
            query = session.query(StatementJournal).filter(StatementJournal.kind == self.kind)
            if program_id:
                query = query.filter(StatementJournal.program_id == program_id)
            if start_date:
                query = query.filter(StatementJournal.entry_date >= start_date)
            if end_date:
                query = query.filter(StatementJournal.entry_date <= end_date)

            rows = query.order_by(StatementJournal.entry_number.desc()).all()
            items: List[Dict[str, Any]] = []
            for r in rows:
                items.append({
                    "id": r.id,
                    "entry_number": r.entry_number,
                    "entry_date": r.entry_date,
                    "listener_full_name": r.listener_full_name,
                    "program_name": r.program_name,
                    "notes": r.notes,
                    "document_path": r.document_path,
                    "listener_id": r.listener_id,
                    "program_id": r.program_id,
                    "created_at": r.created_at,
                })
            if search:
                s = search.strip().lower()
                items = [
                    i for i in items
                    if s in str(i.get("entry_number", "")).lower()
                    or s in (i.get("listener_full_name") or "").lower()
                    or s in (i.get("program_name") or "").lower()
                    or s in (i.get("notes") or "").lower()
                ]
            return items

    def delete_entry(self, entry_id: int) -> bool:
        with DatabaseSession() as session:
            entry = session.query(StatementJournal).get(entry_id)
            if not entry or entry.kind != self.kind:
                return False
            session.delete(entry)
            return True

    # ------------------------------------------------------------------
    # Document rendering
    # ------------------------------------------------------------------
    def _render_document(
        self,
        listener: Listener,
        program: Optional[Program],
        entry_number: int,
        entry_date: date,
        template_name: Optional[str] = None,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        if not template_name:
            return None
        template_path = self.templates_dir / template_name
        if not template_path.exists():
            return None

        context = self._build_context(listener, program, entry_number, entry_date)
        if extra_context:
            context.update(extra_context)

        try:
            doc = DocxTemplate(template_path)
            doc.render(context)
            safe_name = listener.full_name.replace(" ", "_")
            filename = f"{self.config['doc_prefix']}_{entry_number:03d}_{safe_name}.docx"
            output_path = self.output_dir / filename
            doc.save(output_path)
            return str(output_path)
        except Exception as exc:
            print(f"Statement render failed ({self.kind}): {exc}")
            return None

    def _build_context(
        self,
        listener: Listener,
        program: Optional[Program],
        entry_number: int,
        entry_date: date,
    ) -> Dict[str, Any]:
        first_initial = (listener.first_name[0] + ".") if listener.first_name else ""
        middle_initial = (listener.middle_name[0] + ".") if listener.middle_name else ""
        initials_last_name = f"{first_initial}{middle_initial} {listener.last_name or ''}".strip()
        last_name_initials = f"{listener.last_name or ''} {first_initial}{middle_initial}".strip()

        ctx: Dict[str, Any] = {
            "entry_number": entry_number,
            "entry_date": entry_date.strftime("%d.%m.%Y"),
            "entry_year": entry_date.strftime("%Y"),
            # Aliases for template-author convenience
            "number": entry_number,
            "date": entry_date.strftime("%d.%m.%Y"),

            "full_name": listener.full_name,
            "last_name": listener.last_name or "",
            "first_name": listener.first_name or "",
            "middle_name": listener.middle_name or "",
            "initials_last_name": initials_last_name,
            "last_name_initials": last_name_initials,
            "position": listener.position or "",
            "workplace": listener.workplace or "",
            "region": listener.region or "",
            "email": listener.email or "",
        }

        # Gender-aware full name declensions
        gender = getattr(listener, 'gender', None) or 'M'
        decl = self.declension.get_all_declensions(
            listener.last_name or "",
            listener.first_name or "",
            listener.middle_name,
            gender=gender,
        )
        ctx.update(decl)

        if program:
            basis = program.training_basis or ""
            basis_words = basis.split() if basis else []
            basis_instr = " ".join(
                self.declension.decline_word(w, "instrumental") for w in basis_words
            ) if basis_words else ""
            ctx.update({
                "program_name": program.program_name or "",
                "program_short_name": program.program_short_name or program.program_name or "",
                "program_volume": program.program_volume or "",
                "training_period": program.training_period or "",
                "training_duration": program.training_duration or "",
                "education_form": program.education_form or "",
                "education_format": program.education_format or "",
                "training_basis": basis,
                "training_basis_instrumental": basis_instr,
                "training_basis_phrase": f"в соответствии с {basis_instr}" if basis_instr else "",
            })
        else:
            ctx.update({
                "program_name": "",
                "program_short_name": "",
                "program_volume": "",
                "training_period": "",
                "training_duration": "",
                "education_form": "",
                "education_format": "",
                "training_basis": "",
                "training_basis_instrumental": "",
                "training_basis_phrase": "",
            })

        # Grade info (populated if ProgramListener has grade data)
        try:
            from ..database.models import ProgramListener
            with DatabaseSession() as session:
                pl = None
                if program:
                    pl = session.query(ProgramListener).filter(
                        ProgramListener.program_id == program.id,
                        ProgramListener.listener_id == listener.id,
                    ).first()
                if pl and getattr(pl, 'grade_info', None):
                    ctx["grade_info"] = pl.grade_info or ""
                else:
                    ctx["grade_info"] = ""
        except Exception:
            ctx["grade_info"] = ""

        return ctx
