"""Datos semilla del SOC-Lite: roles, usuarios, alertas, triajes, incidentes y bitácora.

Uso:  python -m app.seed            (idempotente, omite si ya hay datos)
      python -m app.seed --reset    (recrea el esquema y siembra de cero)
"""

import asyncio
import hashlib
import random
import sys
from datetime import datetime, timedelta

from app.core.timeutils import utcnow

from sqlalchemy import func, select

from app.core.security import hash_password
from app.database import Base, SessionLocal, engine, init_db
from app.models import Alert, AuditLog, EnrichmentData, Incident, Role, TriageResult, User
from app.services import enrichment as intel
from app.services.triage import _heuristic

ROLES = [
    ("admin", "Administrador con acceso total (usuarios, auditoría, configuración)"),
    ("analyst", "Analista SOC: triaje, alertas, incidentes, reportes"),
    ("viewer", "Lectura de dashboard, alertas, incidentes y reportes"),
]

USERS = [
    ("admin", "admin@soclite.local", "Ana Torres", "Admin123!", "admin"),
    ("analyst", "analyst@soclite.local", "Luis Mendoza", "Analyst123!", "analyst"),
    ("viewer", "viewer@soclite.local", "María Ríos", "Viewer123!", "viewer"),
]

# Reglas estilo Wazuh/OPNsense con IP maliciosas conocidas (datasets públicos, ver docs/datasets.md)
ALERT_TEMPLATES = [
    # (titulo, severidad_origen, rule_id, fuente, ip_maliciosa?)
    ("Posible escaneo de puertos detectado desde IP externa", "media", "100001", "wazuh", True),
    ("Intento de fuerza bruta SSH multiple fallido", "alta", "100101", "wazuh", True),
    ("Malware detectado: coincidencia YARA en fichero descargado", "alta", "100203", "wazuh", True),
    ("Solicitud HTTP hacia dominio de C2 conocido (Snort 2016497)", "alta", "2016497", "wazuh", True),
    ("Actividad sospechosa de usuario: creación de cuenta local", "media", "5712", "wazuh", True),
    ("Escaneo TCP desde IP interna (job de inventario legitimо)", "baja", "4101", "wazuh", False),
    ("DNS fallido repetido hacia servidor DNS publico", "baja", "100004", "opnsense", False),
    ("Solicitud ICMP echo desde host interno", "baja", "100005", "opnsense", False),
    ("Cambio de politica de firewall aplicado por administrador", "media", "5701", "wazuh", False),
    ("Proxy detectado: conexiones salientes inusuales en puerto 8080", "media", "100302", "opnsense", True),
    ("Brute force RDP desde IP reportada en AbuseIPDB", "alta", "100115", "wazuh", True),
    ("Fichero sospechoso en directorio temporal (/tmp)", "media", "100251", "wazuh", True),
    ("Regla antivirus desactivada en endpoint protegido", "alta", "100401", "wazuh", True),
    ("Autenticacion exitosa tras multiples fallos (posible credencial valida)", "alta", "100110", "wazuh", True),
    ("Trafico saliente hacia IP con reputacion baja", "media", "100500", "opnsense", True),
    ("Actualizacion de sistema aplicada automaticamente", "baja", "100601", "wazuh", False),
    ("Certificado TLS proximo a vencer en servicio web", "baja", "100701", "opnsense", False),
    ("Acceso SSH fuera de horario laboral", "media", "100105", "wazuh", False),
    ("Port scan interno detectado desde estacion de desarrollo", "media", "4100", "wazuh", False),
    ("Ejecucion de script con interprete sospechoso (python -c)", "media", "100280", "wazuh", True),
]

MALICIOUS_IPS = list(intel.KNOWN_MALICIOUS_IPS.keys())
BENIGN_IPS = ["192.168.1.45", "192.168.1.102", "192.168.2.15", "10.0.0.24", "10.0.0.88"]
BENIGN_PUBLIC = ["8.8.8.8", "1.1.1.1", "151.101.1.69"]


async def seed(reset: bool = False) -> None:
    if reset:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    await init_db()

    async with SessionLocal() as db:
        existing_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
        if existing_users:
            print("Seed ya aplicado (existentes: %d usuarios). Usa --reset para recrear." % existing_users)
            return

        # --- Roles y usuarios ---
        role_ids: dict[str, int] = {}
        for name, desc in ROLES:
            role = Role(name=name, description=desc)
            db.add(role)
            await db.flush()
            role_ids[name] = role.id
        users: dict[str, User] = {}
        for username, email, full_name, password, role_name in USERS:
            user = User(
                username=username,
                email=email,
                full_name=full_name,
                password_hash=hash_password(password),
                role_id=role_ids[role_name],
            )
            db.add(user)
            await db.flush()
            users[username] = user
        print(f"  roles={len(ROLES)} usuarios={len(USERS)}")

        # --- Alertas (7 días) ---
        rng = random.Random(42)
        now = utcnow()
        alerts: list[Alert] = []
        for i in range(60):
            title, sev, rule_id, source, is_malicious = ALERT_TEMPLATES[i % len(ALERT_TEMPLATES)]
            if is_malicious:
                src_ip = rng.choice(MALICIOUS_IPS)
                dst_ip = rng.choice(BENIGN_IPS)
            else:
                src_ip = rng.choice(BENIGN_IPS if rng.random() < 0.7 else BENIGN_PUBLIC)
                dst_ip = rng.choice(BENIGN_IPS)
            created = now - timedelta(
                days=rng.uniform(0, 6.9), hours=rng.uniform(0, 23), minutes=rng.uniform(0, 59)
            )
            key = hashlib.sha256(f"{source}|{rule_id}|{src_ip}|{dst_ip}|{title}|{i}".encode()).hexdigest()
            alert = Alert(
                source=source,
                rule_id=rule_id,
                severity=sev,
                title=title,
                description=f"Evento correlacionado por la regla {rule_id} ({source}).",
                src_ip=src_ip,
                dst_ip=dst_ip,
                raw_payload={
                    "rule": {"id": rule_id, "level": {"alta": 12, "media": 7, "baja": 3}[sev]},
                    "agent": {"name": f"endpoint-{rng.randint(1, 12):02d}"},
                    "src_ip": src_ip,
                    "dst_ip": dst_ip,
                    "timestamp": created.isoformat() + "Z",
                },
                dedup_hash=key,
                status="pending",
                created_at=created,
            )
            db.add(alert)
            alerts.append(alert)
        await db.flush()
        print(f"  alertas={len(alerts)}")

        # --- Enriquecimiento + triaje (heurístico determinista, sin LLM en seed) ---
        enrich_count = 0
        triaged = 0
        seen_ips: dict[str, dict] = {}
        for alert in alerts:
            ip = alert.src_ip or ""
            if ip and ip not in seen_ips:
                seen_ips[ip] = await intel.enrich_ip(ip)
            data = seen_ips.get(ip, {})
            for tool_name, value in data.items():
                db.add(EnrichmentData(alert_id=alert.id, tool=tool_name, key=ip, value=value))
                enrich_count += 1
            # ~85% de las alertas ya triadas (el resto queda pendiente para la demo)
            if alert.created_at < now - timedelta(hours=6) and rng.random() < 0.8:
                decision = _heuristic(alert, data)
                db.add(
                    TriageResult(
                        alert_id=alert.id,
                        llm_verdict=decision.verdict,
                        predicted_severity=decision.severity,
                        confidence=decision.confidence,
                        summary=decision.summary,
                        recommended_actions=decision.recommended_actions,
                        model_name=None,
                        engine="heuristic",
                        latency_ms=12,
                        created_at=alert.created_at + timedelta(seconds=rng.randint(20, 180)),
                    )
                )
                alert.status = "triaged"
                triaged += 1
        await db.flush()
        print(f"  enrichment={enrich_count} triajes={triaged}")

        # --- Incidentes ---
        high = [a for a in alerts if a.severity == "alta" and a.status == "triaged"][:3]
        incident_specs = [
            ("Fuerza bruta SSH en servidor web perimetral", "alta", "open", "OST-1001"),
            ("Host con posible C2 en la red de oficinas", "alta", "open", "OST-1002"),
            ("Regla antivirus desactivada en portatil de dirección", "media", "closed", "OST-1003"),
        ]
        for idx, (title, sev, status_, ticket) in enumerate(incident_specs):
            alert = high[idx] if idx < len(high) else None
            closed_at = now - timedelta(days=1) if status_ == "closed" else None
            incident = Incident(
                alert_id=alert.id if alert else None,
                title=title,
                severity=sev,
                status=status_,
                assignee_id=users["analyst"].id,
                ticket_id=ticket,
                notes="Generado a partir del triaje automatizado SOC-Lite.",
                opened_at=(alert.created_at if alert else now - timedelta(days=2)),
                closed_at=closed_at,
            )
            db.add(incident)
            if alert:
                alert.status = "escalated"
        await db.flush()
        print(f"  incidentes={len(incident_specs)}")

        # --- Bitácora de auditoría ---
        modules_actions = [
            ("login", "IN"), ("login", "OUT"), ("alerts", "READ"), ("alerts", "CREATE"),
            ("triage", "EXECUTE"), ("reports", "EXPORT"), ("incidents", "READ"),
            ("incidents", "CREATE"), ("metrics", "READ"), ("users", "READ"),
        ]
        usernames = ["admin", "analyst", "viewer"]
        entries = 0
        for i in range(180):
            module, action = rng.choice(modules_actions)
            uname = rng.choice(usernames)
            created = now - timedelta(days=rng.uniform(0, 6.9), hours=rng.uniform(0, 23), minutes=rng.uniform(0, 59))
            db.add(
                AuditLog(
                    user_id=users[uname].id,
                    username=uname,
                    module=module,
                    action=action,
                    method={"IN": "POST", "OUT": "POST", "READ": "GET", "CREATE": "POST", "EXPORT": "GET", "EXECUTE": "POST"}.get(action, "GET"),
                    path=f"/api/v1/{ 'auth' if module == 'login' else module }",
                    ip=f"192.168.1.{rng.randint(10, 60)}",
                    status_code=200,
                    details={"seed": True},
                    created_at=created,
                )
            )
            entries += 1
        await db.commit()
        print(f"  auditoria={entries}")
        print("Seed completado. Credenciales: admin/Admin123! · analyst/Analyst123! · viewer/Viewer123!")


def main() -> None:
    reset = "--reset" in sys.argv
    asyncio.run(seed(reset=reset))


if __name__ == "__main__":
    main()
