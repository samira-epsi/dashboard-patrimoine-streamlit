"""Notification email facultative via SMTP approuvé par l'entreprise.

Configuration dans .env :
  PIPELINE_EMAIL_ENABLED=true
  PIPELINE_EMAIL_TO=adresse@entreprise.fr
  PIPELINE_EMAIL_FROM=adresse-expediteur@entreprise.fr
  PIPELINE_SMTP_HOST=smtp.interne
  PIPELINE_SMTP_PORT=587
  PIPELINE_SMTP_SECURITY=starttls  # starttls | ssl | none
  PIPELINE_SMTP_USER=...           # facultatif si relais interne
  PIPELINE_SMTP_PASSWORD=...       # facultatif si relais interne
  PIPELINE_EMAIL_ATTACH_LOG=false

Outlook/Microsoft 365 ne garantit pas l'authentification SMTP par mot de passe ;
utiliser uniquement une méthode autorisée par la DSI.
"""
from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from .pipeline_logger import PipelineReport, mask_secrets


def _enabled(key: str, default: str = 'false') -> bool:
    return os.getenv(key, default).strip().lower() in {'1', 'true', 'yes', 'oui'}


def _required(key: str) -> str:
    value = os.getenv(key, '').strip()
    if not value:
        raise ValueError(f'Configuration email manquante : {key}')
    return value


def _make_body(report: PipelineReport) -> str:
    parts = [
        'Rapport automatique des pipelines DATA',
        f'Run ID : {report.run_id}',
        f'Dashboard : {report.dashboard}',
        f'Mode opérations : {report.mode}',
        f'Statut final : {report.status}',
        f'Début : {report.started_at}',
        f'Fin : {report.ended_at or "inconnue"}',
        f'Durée : {report.duration_seconds or 0:.1f} secondes',
        '',
        'DÉTAIL DES ÉTAPES',
    ]
    for step in report.steps:
        parts.append(f'- {step.name} : {step.status} ({step.duration_seconds or 0:.1f}s)')
        if step.details:
            parts.append(f'  Détail : {mask_secrets(step.details)[:900]}')
    if report.error:
        parts += ['', 'ERREUR GLOBALE', mask_secrets(report.error)[:2000]]
    parts += ['', 'Consulter le journal local et le report.json pour les détails complets.']
    return '\n'.join(parts)


def send_report(report: PipelineReport, run_dir: Path) -> str:
    """Renvoie DISABLED ou SENT ; lève une exception en cas d'échec SMTP."""
    if not _enabled('PIPELINE_EMAIL_ENABLED'):
        return 'DISABLED'

    recipient = _required('PIPELINE_EMAIL_TO')
    sender = _required('PIPELINE_EMAIL_FROM')
    host = _required('PIPELINE_SMTP_HOST')
    port = int(os.getenv('PIPELINE_SMTP_PORT', '587'))
    security = os.getenv('PIPELINE_SMTP_SECURITY', 'starttls').lower().strip()
    user = os.getenv('PIPELINE_SMTP_USER', '').strip()
    password = os.getenv('PIPELINE_SMTP_PASSWORD', '')
    if security not in {'starttls', 'ssl', 'none'}:
        raise ValueError('PIPELINE_SMTP_SECURITY doit valoir starttls, ssl ou none')
    if bool(user) != bool(password):
        raise ValueError('PIPELINE_SMTP_USER et PIPELINE_SMTP_PASSWORD doivent être tous deux définis ou absents')
    if security == 'none' and (user or password):
        raise ValueError('Authentification sans TLS refusée. Utiliser starttls ou ssl.')

    msg = EmailMessage()
    msg['From'] = sender
    msg['To'] = recipient
    msg['Subject'] = f'[DATA][{report.status}] {report.dashboard.upper()} {report.mode.upper()} | {report.run_id}'
    msg.set_content(_make_body(report))

    if _enabled('PIPELINE_EMAIL_ATTACH_LOG'):
        # Logs parfois volumineux et sensibles ; pièce jointe désactivée par défaut.
        path = run_dir / 'pipeline.log'
        content = path.read_text(encoding='utf-8', errors='replace')
        content = mask_secrets(content)
        if len(content.encode('utf-8')) > 2_000_000:
            content = content[-200_000:]
        msg.add_attachment(content.encode('utf-8'), maintype='text', subtype='plain', filename='pipeline.log')

    timeout = 30
    if security == 'ssl':
        with smtplib.SMTP_SSL(host, port, timeout=timeout, context=ssl.create_default_context()) as smtp:
            if user:
                smtp.login(user, password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=timeout) as smtp:
            smtp.ehlo()
            if security == 'starttls':
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
            if user:
                smtp.login(user, password)
            smtp.send_message(msg)
    return 'SENT'
