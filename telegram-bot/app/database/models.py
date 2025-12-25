"""Модели базы данных."""
from datetime import datetime
from typing import Optional
from uuid import UUID
from sqlalchemy import BigInteger, String, Boolean, DateTime, func, Enum as SQLEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum


class Base(DeclarativeBase):
    """Базовый класс для всех моделей."""
    pass


class PaymentStatus(enum.Enum):
    """Статусы оплаты (DEPRECATED - используйте SubscriptionStatus)."""
    free = "free"
    pending = "pending"
    active = "active"
    expired = "expired"
    PAID = "PAID"  # Existing value in DB


class SubscriptionStatus(enum.Enum):
    """Статусы подписки (новая унифицированная система)."""
    FREE = "FREE"      # Бесплатный доступ (legacy users, grandfathered)
    TRIAL = "TRIAL"    # Триальный период
    PAID = "PAID"      # Активная подписка
    EXPIRED = "EXPIRED"  # Истекшая подписка


class User(Base):
    """Модель пользователя."""
    
    __tablename__ = 'users'
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
    wb_api_key: Mapped[str] = mapped_column(String(500), nullable=True, default=None)
    google_sheet_id: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    payment_status: Mapped[PaymentStatus] = mapped_column(SQLEnum(PaymentStatus, name='payment_status_enum', create_constraint=False), default=PaymentStatus.free, nullable=False)
    google_sheet_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        server_default=func.now(), 
        onupdate=func.now()
    )
    
    def __repr__(self) -> str:
        """Строковое представление пользователя."""
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, full_name='{self.full_name}')>"


class Subscription(Base):
    """
    Модель подписки пользователя.
    
    Единый источник правды для проверки доступа к сервису.
    Используется как telegram-ботом, так и admin-панелью.
    """
    
    __tablename__ = 'subscriptions'
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        ForeignKey('users.id', ondelete='CASCADE'), 
        unique=True, 
        nullable=False, 
        index=True
    )
    
    # Статус и доступ
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False, 
        default='FREE',
        index=True
    )
    has_access: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Даты для управления доступом
    trial_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    subscription_starts_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    subscription_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Метаданные платежей
    payment_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    payment_external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_payment_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )
    
    def __repr__(self) -> str:
        """Строковое представление подписки."""
        return f"<Subscription(user_id={self.user_id}, status='{self.status}', has_access={self.has_access})>"
    
    def grant_access(self) -> None:
        """Выдать доступ и установить статус PAID."""
        self.has_access = True
        self.status = 'PAID'
    
    def revoke_access(self) -> None:
        """Отозвать доступ и установить статус EXPIRED."""
        self.has_access = False
        self.status = 'EXPIRED'
