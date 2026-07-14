from sqlalchemy import Text, ForeignKey, DateTime, ARRAY, String
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from datetime import datetime


class Base(AsyncAttrs, DeclarativeBase):
    pass



class Vacancy(Base):
    __tablename__ = "vacancies"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[int] = mapped_column(unique=True)
    is_hidden: Mapped[bool]
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str]
    employer_name: Mapped[str | None]
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    requirement: Mapped[str | None] = mapped_column(Text)
    responsibility: Mapped[str | None] = mapped_column(Text)
    query_hits: Mapped[list[str]] = mapped_column(ARRAY(String))

    details: Mapped["VacancyDetails | None"] = relationship(cascade="all, delete-orphan")
    ai_analysis: Mapped["AIAnalysis | None"] = relationship(cascade="all, delete-orphan")


class VacancyDetails(Base):
    __tablename__ = "vacancy_details"

    vacancy_id: Mapped[int] = mapped_column(
        ForeignKey("vacancies.id", ondelete="CASCADE"),
        primary_key=True,
    )
    description: Mapped[str] = mapped_column(Text)
    salary_from: Mapped[int | None]
    salary_to: Mapped[int | None]
    salary_currency: Mapped[str | None]
    experience: Mapped[str | None]
    employment: Mapped[str | None]
    schedule: Mapped[str | None]
    key_skills: Mapped[list[str]] = mapped_column(ARRAY(String))
    work_formats: Mapped[list[str]] = mapped_column(ARRAY(String))


class AIAnalysis(Base):
    __tablename__ = "ai_analysis"

    vacancy_id: Mapped[int] = mapped_column(ForeignKey("vacancies.id", ondelete="CASCADE"), primary_key=True,)
    explanation: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float]
    is_relevant: Mapped[bool]





