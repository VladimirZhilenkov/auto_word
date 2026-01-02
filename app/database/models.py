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
    ForeignKey, UniqueConstraint, Index
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
    
    # Рабочая информация
    position: Mapped[Optional[str]] = mapped_column(String(255))  # Должность
    workplace: Mapped[Optional[str]] = mapped_column(String(255))  # Место работы
    region: Mapped[Optional[str]] = mapped_column(String(255))  # Субъект РФ
    
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
