"""Journalisation centralisée des exécutions des pipelines.

Ne stocke pas de mots de passe ni de variables d'environnement dans les rapports.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')


def mask_secrets(value: str) -> str:
    """Masquage prudent des secrets courants dans les sorties et exceptions."""
    value = re.sub(r'(?i)(authorization\s*:\s*bearer\s+)\S+', r'\1[MASQUE]', value)
    value = re.sub(r'(?i)\b(password|passwd|token|api[_-]?key|client[_-]?secret)\s*[=:]\s*([^\s,;]+)', r'\1=[MASQUE]', value)
    value = re.sub(r'(?i)(postgres(?:ql)?(?:\+\w+)?://[^:\s/@]+:)[^@\s]+(@)', r'\1[MASQUE]\2', value)
    return value


class MaskingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return mask_secrets(super().format(record))


@dataclass
class StepResult:
    name: str
    status: str = 'PENDING'
    started_at: str | None = None
    ended_at: str | None = None
    duration_seconds: float | None = None
    details: str = ''
    log_file: str = ''


@dataclass
class PipelineReport:
    run_id: str
    dashboard: str
    mode: str
    started_at: str
    status: str = 'RUNNING'
    ended_at: str | None = None
    duration_seconds: float | None = None
    error: str = ''
    steps: list[StepResult] = field(default_factory=list)
    notification_status: str = 'NOT_ATTEMPTED'

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def create_run(dashboard: str, mode: str, root: Path) -> tuple[PipelineReport, logging.Logger, Path]:
    run_id = f'{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:8]}'
    run_dir = root / 'logs' / 'pipeline' / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    logger = logging.getLogger(f'pipeline.{run_id}')
    logger.setLevel(logging.INFO)
    logger.propagate = False
    formatter = MaskingFormatter('%(asctime)s | %(levelname)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    logfile = logging.FileHandler(run_dir / 'pipeline.log', encoding='utf-8')
    logfile.setFormatter(formatter)
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(logfile)
    logger.addHandler(console)
    report = PipelineReport(run_id=run_id, dashboard=dashboard, mode=mode, started_at=now_iso())
    save_report(report, run_dir)
    return report, logger, run_dir


def save_report(report: PipelineReport, run_dir: Path) -> None:
    """Écriture atomique locale du bilan JSON."""
    file_path = run_dir / 'report.json'
    temp_path = run_dir / 'report.json.tmp'
    temp_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    os.replace(temp_path, file_path)


def close_logger(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        handler.flush()
        handler.close()
        logger.removeHandler(handler)
