from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), default="SECRETARIA", nullable=False)
    secretaria_id: Mapped[int | None] = mapped_column(ForeignKey("secretarias.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    secretaria = relationship("Secretaria")

class Secretaria(Base):
    __tablename__ = "secretarias"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(180), nullable=False)
    sigla: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    ativa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

class UnidadeGestora(Base):
    __tablename__ = "unidades_gestoras"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(180), nullable=False)
    codigo_etce: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    secretaria_id: Mapped[int] = mapped_column(ForeignKey("secretarias.id"), nullable=False)
    secretaria = relationship("Secretaria")

class Programa(Base):
    __tablename__ = "programas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(220), nullable=False)
    codigo_etce: Mapped[int | None] = mapped_column(Integer, nullable=True)
    secretaria_id: Mapped[int] = mapped_column(ForeignKey("secretarias.id"), nullable=False)
    unidade_id: Mapped[int] = mapped_column(ForeignKey("unidades_gestoras.id"), nullable=False)
    norma_instituidora: Mapped[str | None] = mapped_column(String(300), nullable=True)
    vigente: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    homologado_etce: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    criterios_padrao_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    secretaria = relationship("Secretaria")
    unidade = relationship("UnidadeGestora")
    criterios_vinculados = relationship("ProgramaCriterio", cascade="all, delete-orphan", back_populates="programa")


class ProgramaCriterio(Base):
    __tablename__ = "programa_criterios"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    programa_id: Mapped[int] = mapped_column(ForeignKey("programas.id"), nullable=False, index=True)
    identificador_criterio: Mapped[int] = mapped_column(Integer, nullable=False)
    nome: Mapped[str] = mapped_column(String(250), nullable=False)
    categoria: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tipo_dado: Mapped[str] = mapped_column(String(30), nullable=False)
    limite_inferior: Mapped[str | None] = mapped_column(String(100), nullable=True)
    limite_superior: Mapped[str | None] = mapped_column(String(100), nullable=True)
    vigencia_inicio: Mapped[str | None] = mapped_column(String(10), nullable=True)
    vigencia_fim: Mapped[str | None] = mapped_column(String(10), nullable=True)
    prazo_indeterminado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    programa = relationship("Programa", back_populates="criterios_vinculados")

class Beneficiario(Base):
    __tablename__ = "beneficiarios"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cpf: Mapped[str] = mapped_column(String(11), unique=True, index=True, nullable=False)
    numero_nis: Mapped[str | None] = mapped_column(String(11), nullable=True)
    nome: Mapped[str] = mapped_column(String(250), nullable=False)
    sexo: Mapped[str] = mapped_column(String(1), nullable=False)
    data_nascimento: Mapped[str] = mapped_column(String(10), nullable=False)
    nacionalidade: Mapped[str] = mapped_column(String(150), nullable=False, default="Brasileira")
    nome_mae: Mapped[str | None] = mapped_column(String(250), nullable=True)
    endereco_cep: Mapped[str | None] = mapped_column(String(8), nullable=True)
    logradouro: Mapped[str] = mapped_column(String(500), nullable=False)
    bairro: Mapped[str] = mapped_column(String(250), nullable=False)
    numero: Mapped[str | None] = mapped_column(String(50), nullable=True)
    complemento: Mapped[str | None] = mapped_column(String(100), nullable=True)
    codigo_ibge_municipio: Mapped[str] = mapped_column(String(7), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class Folha(Base):
    __tablename__ = "folhas"
    __table_args__ = (UniqueConstraint("programa_id", "ano", "mes", "tipo_folha", "sequencial", name="uq_folha_competencia"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    programa_id: Mapped[int] = mapped_column(ForeignKey("programas.id"), nullable=False)
    unidade_id: Mapped[int] = mapped_column(ForeignKey("unidades_gestoras.id"), nullable=False)
    ano: Mapped[str] = mapped_column(String(4), nullable=False)
    mes: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo_folha: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    sequencial: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(40), default="RASCUNHO", nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    secretaria_certified_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    financas_certified_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    cgm_certified_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    programa = relationship("Programa")
    unidade = relationship("UnidadeGestora")
    itens = relationship("FolhaItem", cascade="all, delete-orphan", back_populates="folha")

class FolhaItem(Base):
    __tablename__ = "folha_itens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    folha_id: Mapped[int] = mapped_column(ForeignKey("folhas.id"), nullable=False, index=True)
    beneficiario_id: Mapped[int] = mapped_column(ForeignKey("beneficiarios.id"), nullable=False)
    valor_total_transferido: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_pessoas_beneficio: Mapped[int] = mapped_column(Integer, nullable=False)
    total_dependentes_beneficio: Mapped[int] = mapped_column(Integer, nullable=False)
    criterios_json: Mapped[str] = mapped_column(Text, nullable=False)
    dependentes_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidencia: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    folha = relationship("Folha", back_populates="itens")
    beneficiario = relationship("Beneficiario")

class ValidationIssue(Base):
    __tablename__ = "validation_issues"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    folha_id: Mapped[int] = mapped_column(ForeignKey("folhas.id"), nullable=False, index=True)
    item_id: Mapped[int | None] = mapped_column(ForeignKey("folha_itens.id"), nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # BLOCK / ALERT
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    item = relationship("FolhaItem")

class DeletionRequest(Base):
    __tablename__ = "deletion_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    target_type: Mapped[str] = mapped_column(String(40), nullable=False)  # FOLHA / FOLHA_ITEM / PROGRAMA / SECRETARIA / UG / USER
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    folha_id: Mapped[int | None] = mapped_column(ForeignKey("folhas.id"), nullable=True)
    secretaria_id: Mapped[int | None] = mapped_column(ForeignKey("secretarias.id"), nullable=True)
    requested_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="PENDENTE", nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    requester = relationship("User", foreign_keys=[requested_by])
    decider = relationship("User", foreign_keys=[decided_by])
    secretaria = relationship("Secretaria")
    folha = relationship("Folha")

class Remessa(Base):
    __tablename__ = "remessas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    folha_id: Mapped[int] = mapped_column(ForeignKey("folhas.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(300), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="GERADA", nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    folha = relationship("Folha")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    user = relationship("User")
