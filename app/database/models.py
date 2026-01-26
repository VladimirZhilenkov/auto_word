"""
SQLAlchemy ORM models for Document Generator application.

Database Schema:
- Listener (Слушатель) - training program participant
- Program (Программа обучения) - training program
- ProgramListener - many-to-many association with additional data
"""

from datetime import datetime, date
from typing import List, Optional

from sqlalchemy import (
    Column, Integer, String, Date, DateTime, Text,
    ForeignKey, UniqueConstraint, Index, func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class ProgramListener(Base):
    """
    Association table for Program-Listener many-to-many relationship.
    Contains additional data about the enrollment.
    """
    __tablename__ = 'program_listeners'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    program_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey('programs.id', ondelete='CASCADE'),
        nullable=False
    )
    listener_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey('listeners.id', ondelete='CASCADE'),
        nullable=False
    )
    order_number: Mapped[Optional[int]] = mapped_column(Integer)  # № п/п в документе
    enrollment_date: Mapped[Optional[date]] = mapped_column(Date)  # Дата зачисления
    
    # Relationships
    program: Mapped["Program"] = relationship(back_populates="listener_associations")
    listener: Mapped["Listener"] = relationship(back_populates="program_associations")
    
    __table_args__ = (
        UniqueConstraint('program_id', 'listener_id', name='uq_program_listener'),
        Index('ix_program_listeners_program', 'program_id'),
        Index('ix_program_listeners_listener', 'listener_id'),
    )
    
    def __repr__(self):
        return f"<ProgramListener(program_id={self.program_id}, listener_id={self.listener_id})>"


class Listener(Base):
    """
    Слушатель (участник программы обучения).
    Listener model representing a training program participant.
    """
    __tablename__ = 'listeners'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # ФИО (разбивается при импорте)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)  # Фамилия
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)  # Имя
    middle_name: Mapped[Optional[str]] = mapped_column(String(100))  # Отчество
    
    # Дата рождения
    birth_date: Mapped[Optional[date]] = mapped_column(Date)  # Дата рождения
    
    # Рабочая информация
    position: Mapped[Optional[str]] = mapped_column(String(255))  # Должность
    workplace: Mapped[Optional[str]] = mapped_column(String(255))  # Место работы
    region: Mapped[Optional[str]] = mapped_column(String(255))  # Субъект РФ
    
    # Контактная информация
    mobile_phone: Mapped[Optional[str]] = mapped_column(String(50))  # Мобильный телефон
    work_phone: Mapped[Optional[str]] = mapped_column(String(50))  # Рабочий телефон
    email: Mapped[Optional[str]] = mapped_column(String(255))  # Электронная почта
    
    # Паспортные данные
    passport_series_number: Mapped[Optional[str]] = mapped_column(String(20))  # Серия и номер паспорта
    passport_issue_date: Mapped[Optional[date]] = mapped_column(Date)  # Дата выдачи
    passport_issued_by: Mapped[Optional[str]] = mapped_column(String(500))  # Кем выдан
    passport_department_code: Mapped[Optional[str]] = mapped_column(String(20))  # Код подразделения
    
    # Адреса
    registration_address: Mapped[Optional[str]] = mapped_column(String(500))  # Адрес регистрации с индексом
    actual_address: Mapped[Optional[str]] = mapped_column(String(500))  # Фактический адрес с индексом
    
    # Идентификационные данные
    snils: Mapped[Optional[str]] = mapped_column(String(20))  # СНИЛС
    inn: Mapped[Optional[str]] = mapped_column(String(20))  # ИНН
    
    # Согласие на обработку персональных данных
    personal_data_consent: Mapped[bool] = mapped_column(Integer, default=False)  # Согласие на обработку ПД
    
    # Метаданные
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.now, 
        onupdate=datetime.now
    )
    notes: Mapped[Optional[str]] = mapped_column(Text)  # Примечания
    
    # Relationships
    program_associations: Mapped[List["ProgramListener"]] = relationship(
        back_populates="listener",
        cascade="all, delete-orphan"
    )
    programs: Mapped[List["Program"]] = relationship(
        secondary="program_listeners",
        back_populates="listeners",
        viewonly=True
    )
    
    __table_args__ = (
        Index('ix_listeners_name', 'last_name', 'first_name'),
        Index('ix_listeners_region', 'region'),
    )
    
    @property
    def full_name(self) -> str:
        """Get full name as 'Фамилия Имя Отчество'."""
        parts = [self.last_name, self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        return ' '.join(parts)
    
    @property
    def initials(self) -> str:
        """Get name with initials as 'Фамилия И.О.'"""
        fi = self.first_name[0] if self.first_name else ""
        mi = self.middle_name[0] if self.middle_name else ""
        if mi:
            return f"{self.last_name} {fi}.{mi}."
        return f"{self.last_name} {fi}."
    
    @property
    def initials_before(self) -> str:
        """Get initials before surname as 'И.О. Фамилия'"""
        fi = self.first_name[0] if self.first_name else ""
        mi = self.middle_name[0] if self.middle_name else ""
        if mi:
            return f"{fi}.{mi}. {self.last_name}"
        return f"{fi}. {self.last_name}"
    
    def __repr__(self):
        return f"<Listener(id={self.id}, name='{self.full_name}')>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'last_name': self.last_name,
            'first_name': self.first_name,
            'middle_name': self.middle_name,
            'full_name': self.full_name,
            'position': self.position,
            'workplace': self.workplace,
            'region': self.region,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'notes': self.notes,
        }


class Program(Base):
    """
    Программа обучения (Training Program).
    """
    __tablename__ = 'programs'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Основные данные программы
    program_name: Mapped[str] = mapped_column(Text, nullable=False)  # Наименование программы
    program_short_name: Mapped[Optional[str]] = mapped_column(String(255))  # Краткое наименование
    training_basis: Mapped[Optional[str]] = mapped_column(String(100))  # Основание (контракт/договор)
    training_period: Mapped[Optional[str]] = mapped_column(String(100))  # Период обучения
    program_volume: Mapped[Optional[str]] = mapped_column(String(100))  # Объем программы
    education_form: Mapped[Optional[str]] = mapped_column(String(50))  # Форма обучения
    education_format: Mapped[Optional[str]] = mapped_column(Text)  # Формат обучения
    listener_category: Mapped[Optional[str]] = mapped_column(String(255))  # Категория слушателей
    expulsion_date: Mapped[Optional[date]] = mapped_column(Date)  # Дата отчисления
    
    # Метаданные
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.now, 
        onupdate=datetime.now
    )
    
    # Relationships
    listener_associations: Mapped[List["ProgramListener"]] = relationship(
        back_populates="program",
        cascade="all, delete-orphan"
    )
    listeners: Mapped[List["Listener"]] = relationship(
        secondary="program_listeners",
        back_populates="programs",
        viewonly=True
    )
    
    __table_args__ = (
        Index('ix_programs_name', 'program_name'),
        Index('ix_programs_date', 'expulsion_date'),
    )
    
    @property
    def display_name(self) -> str:
        """Get display name (short name if available, else full name truncated)."""
        if self.program_short_name:
            return self.program_short_name
        if self.program_name and len(self.program_name) > 50:
            return self.program_name[:50] + "..."
        return self.program_name or ""
    
    @property
    def formatted_expulsion_date(self) -> str:
        """Get formatted expulsion date."""
        if self.expulsion_date:
            return self.expulsion_date.strftime("%d.%m.%Y")
        return ""
    
    def __repr__(self):
        return f"<Program(id={self.id}, name='{self.display_name}')>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'program_name': self.program_name,
            'program_short_name': self.program_short_name,
            'training_basis': self.training_basis,
            'training_period': self.training_period,
            'program_volume': self.program_volume,
            'education_form': self.education_form,
            'education_format': self.education_format,
            'listener_category': self.listener_category,
            'expulsion_date': self.expulsion_date.isoformat() if self.expulsion_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

class DocumentRegister(Base):
    """
    Document register entry for tracking generated documents.
    Registers documents with automatic sequential numbering by type.
    """
    __tablename__ = 'document_register'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    number: Mapped[int] = mapped_column(Integer, nullable=False)  # Sequential number per type
    document_type: Mapped[str] = mapped_column(
        String(50), 
        nullable=False
    )  # enrollment, admission, graduation, order
    document_path: Mapped[str] = mapped_column(
        String(500), 
        nullable=False
    )  # Path to generated document
    listener_id: Mapped[Optional[int]] = mapped_column(Integer)  # Associated listener
    program_id: Mapped[Optional[int]] = mapped_column(Integer)  # Associated program
    listener_name: Mapped[str] = mapped_column(
        String(255), 
        nullable=False
    )  # Full name for reference
    registration_date: Mapped[date] = mapped_column(
        Date, 
        nullable=False, 
        default=date.today
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    extra_data: Mapped[Optional[str]] = mapped_column(Text)  # JSON metadata
    
    __table_args__ = (
        Index('ix_register_type_number', 'document_type', 'number'),
        Index('ix_register_date', 'registration_date'),
    )
    
    def __repr__(self):
        return f"<DocumentRegister(number={self.number}, type={self.document_type})>"


class OrderJournal(Base):
    """
    Журнал регистрации приказов по личному составу.
    Независимая нумерация по типам: enrollment, admission, graduation.
    """
    __tablename__ = 'order_journal'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    journal_type: Mapped[str] = mapped_column(String(50), nullable=False)  # enrollment/admission/graduation
    order_number: Mapped[int] = mapped_column(Integer, nullable=False)  # Порядковый номер в журнале для типа
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)  # Наименование/краткое содержание
    executor: Mapped[str] = mapped_column(String(255), nullable=False)  # Ответственный исполнитель

    # Связь с программой (необязательная), плюс дублирование названия для истории
    program_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey('programs.id', ondelete='SET NULL'), nullable=True
    )
    program_name: Mapped[Optional[str]] = mapped_column(Text)  # Историческое имя программы

    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    document_path: Mapped[Optional[str]] = mapped_column(String(500))

    # Отношение к объекту Program (без каскадного удаления записей журнала)
    program: Mapped[Optional["Program"]] = relationship(viewonly=True)

    __table_args__ = (
        # Уникальность номера в пределах типа журнала
        UniqueConstraint('journal_type', 'order_number', name='uq_order_journal_type_number'),
        Index('ix_order_journal_type_number', 'journal_type', 'order_number'),
        Index('ix_order_journal_date', 'order_date'),
    )

    def __repr__(self):
        return f"<OrderJournal(type={self.journal_type}, number={self.order_number})>"


class ContractJournal(Base):
    """
    Журнал регистрации договоров.
    Хранит ссылку на слушателя и программу, а также исторические данные.
    """

    __tablename__ = 'contract_journal'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_number: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    contract_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Связи
    listener_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey('listeners.id', ondelete='SET NULL')
    )
    program_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey('programs.id', ondelete='SET NULL')
    )

    # Исторические данные на момент создания договора
    listener_full_name: Mapped[Optional[str]] = mapped_column(String(255))
    program_name: Mapped[Optional[str]] = mapped_column(String(500))

    # Дополнительные поля договора
    contract_sum: Mapped[Optional[str]] = mapped_column(String(100))
    payment_type: Mapped[Optional[str]] = mapped_column(String(100))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    document_path: Mapped[Optional[str]] = mapped_column(String(500))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Отношения
    listener: Mapped[Optional["Listener"]] = relationship(backref="contracts")
    program: Mapped[Optional["Program"]] = relationship(backref="contracts")

    __table_args__ = (
        Index('ix_contract_journal_date', 'contract_date'),
    )

    def __repr__(self):
        return f"<ContractJournal(number={self.contract_number}, listener={self.listener_full_name})>"