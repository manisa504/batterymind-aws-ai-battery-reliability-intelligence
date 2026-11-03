from __future__ import annotations

import json
from functools import lru_cache

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.orm import sessionmaker

from packages.battery_analytics import capacity_analysis
from packages.decision_engine import classify
from packages.memory_engine import Base, MemoryRepository
from packages.prediction import estimate_linear_rul

from .auth import Principal, current_principal
from .settings import settings

app = FastAPI(title="BatteryMind API", version="0.1.0", docs_url="/api/docs")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.allowed_origin],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-BatteryMind-User"],
)
engine = create_engine(settings.resolved_database_url)
SessionFactory = sessionmaker(bind=engine)
Base.metadata.create_all(engine)


@lru_cache
def cycles() -> pd.DataFrame:
    path = settings.processed_data_dir / "cycles.parquet"
    if not path.exists():
        raise RuntimeError("Processed data is unavailable; run the verified ingestion pipeline")
    return pd.read_parquet(path)


def db_session():
    with SessionFactory() as session:
        yield session


class SessionCreate(BaseModel):
    battery_id: str = Field(pattern=r"^B\d{4}$")
    objective: str = Field(min_length=1, max_length=500)


class AssessmentCreate(BaseModel):
    session_id: str
    battery_id: str = Field(pattern=r"^B\d{4}$")
    cutoff_cycle: int = Field(gt=0)
    idempotency_key: str = Field(min_length=8, max_length=128)
    supersedes_id: str | None = None
    expected_version: int | None = Field(default=None, gt=0)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "region": settings.aws_region,
        "data_available": (settings.processed_data_dir / "cycles.parquet").exists(),
    }


@app.get("/api/v1/batteries")
def batteries():
    frame = cycles()
    return {
        "items": [
            {"battery_id": cell, "discharge_measurements": int(len(rows[rows.type == "discharge"]))}
            for cell, rows in frame.groupby("battery_id")
        ],
        "provenance_manifest": "data/manifests/nasa-source.json",
    }


@app.get("/api/v1/batteries/{battery_id}/analysis")
def analysis(battery_id: str, cutoff: int | None = Query(default=None, gt=0)):
    try:
        result = capacity_analysis(cycles(), battery_id, cutoff)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    result["classification"] = classify(result["soh_percent"], len(result["measurements"])).__dict__
    result["rul"] = estimate_linear_rul(
        [x["cycle"] for x in result["measurements"]], [x["capacity_ah"] for x in result["measurements"]]
    )
    result["provenance"] = {
        "dataset": "NASA Ames Li-ion Battery Aging Datasets",
        "manifest": "data/manifests/nasa-source.json",
        "measurement_kind": "laboratory_experiment",
    }
    return result


@app.post("/api/v1/sessions", status_code=201)
def create_session(
    payload: SessionCreate, principal: Principal = Depends(current_principal), db: DbSession = Depends(db_session)
):
    if payload.battery_id not in set(cycles()["battery_id"]):
        raise HTTPException(status_code=404, detail="Unknown battery ID")
    record = MemoryRepository(db, principal.user_id).create_session(payload.battery_id, payload.objective)
    return {"id": record.id, "battery_id": record.battery_id, "objective": record.objective}


@app.post("/api/v1/assessments", status_code=201)
def create_assessment(
    payload: AssessmentCreate,
    response: Response,
    principal: Principal = Depends(current_principal),
    db: DbSession = Depends(db_session),
):
    analysis_result = analysis(payload.battery_id, payload.cutoff_cycle)
    classification = analysis_result["classification"]
    explanation = classification["rationale"]
    try:
        record = MemoryRepository(db, principal.user_id).store_assessment(
            session_id=payload.session_id,
            battery_id=payload.battery_id,
            cutoff_cycle=payload.cutoff_cycle,
            decision=str(classification["decision"]),
            explanation=explanation,
            evidence=analysis_result,
            policy_version=classification["policy_version"],
            model_version=None,
            idempotency_key=payload.idempotency_key,
            supersedes_id=payload.supersedes_id,
            expected_version=payload.expected_version,
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    response.headers["ETag"] = f'"{record.version}"'
    return {
        "id": record.id,
        "decision": record.decision,
        "cutoff_cycle": record.cutoff_cycle,
        "validity": record.validity,
        "explanation": record.explanation,
    }


@app.get("/api/v1/batteries/{battery_id}/assessments")
def assessment_history(
    battery_id: str,
    cutoff: int = Query(gt=0),
    principal: Principal = Depends(current_principal),
    db: DbSession = Depends(db_session),
):
    records = MemoryRepository(db, principal.user_id).valid_history(battery_id, cutoff)
    return {
        "items": [
            {
                "id": x.id,
                "cutoff_cycle": x.cutoff_cycle,
                "decision": x.decision,
                "explanation": x.explanation,
                "policy_version": x.policy_version,
                "evidence": json.loads(x.evidence_json),
            }
            for x in records
        ]
    }


@app.delete("/api/v1/assessments/{assessment_id}", status_code=204)
def delete_assessment(
    assessment_id: str, principal: Principal = Depends(current_principal), db: DbSession = Depends(db_session)
):
    if not MemoryRepository(db, principal.user_id).delete_assessment(assessment_id):
        raise HTTPException(status_code=404, detail="Assessment not found")


@app.get("/api/v1/evaluation")
def evaluation():
    return {
        "status": "available_after_executed_evaluation",
        "reports": ["reports/model_evaluation/rul-baselines.json", "reports/memory/memory-tests.json"],
        "live_aws_validation": "BLOCKED",
    }
