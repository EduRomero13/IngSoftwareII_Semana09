import pytest

pytestmark = pytest.mark.integration


async def login(client, username: str, password: str) -> str:
    resp = await client.post(
        "/api/v1/auth/login/json", json={"username": username, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_health(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["api"] == "ok"
    assert body["database"] == "ok"


async def test_login_ok_y_fallido(client):
    token = await login(client, "analyst", "Analyst123!")
    assert len(token) > 50
    resp = await client.post(
        "/api/v1/auth/login/json", json={"username": "analyst", "password": "mala"}
    )
    assert resp.status_code == 401


async def test_endpoints_requieren_token(client):
    assert (await client.get("/api/v1/alerts")).status_code == 401
    assert (await client.get("/api/v1/metrics/overview")).status_code == 401
    assert (await client.get("/api/v1/users")).status_code == 401
    assert (await client.get("/api/v1/audit")).status_code == 401


async def test_rbac_permisos_por_rol(client):
    viewer = await login(client, "viewer", "Viewer123!")
    analyst = await login(client, "analyst", "Analyst123!")
    admin = await login(client, "admin", "Admin123!")

    # viewer: lectura permitida, triaje y usuarios prohibidos
    assert (await client.get("/api/v1/alerts", headers=auth(viewer))).status_code == 200
    assert (await client.post("/api/v1/triage/1", headers=auth(viewer))).status_code == 403
    assert (await client.get("/api/v1/users", headers=auth(viewer))).status_code == 403

    # analyst: triaje si, gestion de usuarios no
    assert (await client.get("/api/v1/users", headers=auth(analyst))).status_code == 403

    # admin: todo
    assert (await client.get("/api/v1/users", headers=auth(admin))).status_code == 200

    # permisos declarados en el token
    resp = await client.post(
        "/api/v1/auth/login/json",
        json={"username": "viewer", "password": "Viewer123!"},
    )
    perms = resp.json()["permissions"]
    assert "alerts.read" in perms
    assert "triage.execute" not in perms
    assert "users.manage" not in perms


async def test_alertas_crud_y_webhook_dedup(client):
    analyst = await login(client, "analyst", "Analyst123!")
    payload = {
        "source": "wazuh",
        "severity": "alta",
        "title": "Alerta de prueba C2",
        "rule_id": "2016497",
        "src_ip": "194.26.229.11",
        "dst_ip": "192.168.1.50",
        "raw_payload": {"rule": {"id": "2016497"}},
    }
    resp = await client.post("/api/v1/alerts", json=payload, headers=auth(analyst))
    assert resp.status_code == 201
    alert_id = resp.json()["id"]

    detail = await client.get(f"/api/v1/alerts/{alert_id}", headers=auth(analyst))
    assert detail.status_code == 200
    assert detail.json()["status"] == "pending"

    # webhook sin token -> 401
    assert (await client.post("/api/v1/alerts/webhook", json=payload)).status_code == 401
    # webhook con token -> acepta; duplicado devuelve la misma alerta
    wh = await client.post(
        "/api/v1/alerts/webhook",
        json=payload,
        headers={"X-Webhook-Token": "soclite-webhook-token"},
    )
    assert wh.status_code == 202
    assert wh.json()["id"] == alert_id

    # cambio de estado
    resp = await client.patch(
        f"/api/v1/alerts/{alert_id}", json={"status": "closed"}, headers=auth(analyst)
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"


async def test_triaje_y_auditoria(client):
    analyst = await login(client, "analyst", "Analyst123!")
    resp = await client.post(
        "/api/v1/alerts",
        json={
            "source": "wazuh",
            "severity": "alta",
            "title": "Fuerza bruta SSH",
            "rule_id": "100101",
            "src_ip": "193.32.162.229",
            "dst_ip": "192.168.1.60",
        },
        headers=auth(analyst),
    )
    alert_id = resp.json()["id"]

    triage = await client.post(f"/api/v1/triage/{alert_id}", headers=auth(analyst))
    assert triage.status_code == 200, triage.text
    body = triage.json()
    assert body["llm_verdict"] in {"verdadero_positivo", "falso_positivo", "sospechoso"}
    assert body["predicted_severity"] in {"alta", "media", "baja"}
    assert body["summary"]
    assert isinstance(body["recommended_actions"], list)
    assert body["engine"] in {"llm", "heuristic"}

    # la alerta queda triada
    detail = (await client.get(f"/api/v1/alerts/{alert_id}", headers=auth(analyst))).json()
    assert detail["status"] == "triaged"
    assert detail["triage"] is not None
    assert detail["enrichments"]

    # la ejecucion del triaje queda en la bitacora (modulo triage, accion EXECUTE)
    admin = await login(client, "admin", "Admin123!")
    audit = (
        await client.get(
            "/api/v1/audit?module=triage&action=EXECUTE&page_size=50", headers=auth(admin)
        )
    ).json()
    assert any(
        e["details"] and e["details"].get("alert_id") == alert_id for e in audit["items"]
    )


async def test_metricas_dashboard(client):
    analyst = await login(client, "analyst", "Analyst123!")
    body = (await client.get("/api/v1/metrics/overview", headers=auth(analyst))).json()
    for key in (
        "total_alerts",
        "pending_alerts",
        "triaged_alerts",
        "open_incidents",
        "avg_mttt_seconds",
        "false_positive_rate",
        "by_severity",
        "top_sources",
        "trend",
    ):
        assert key in body
    assert body["total_alerts"] >= 1


async def test_reportes_pdf_word_excel(client):
    analyst = await login(client, "analyst", "Analyst123!")
    for report_type in ("operational", "management"):
        pdf = await client.get(
            f"/api/v1/reports?type={report_type}&format=pdf", headers=auth(analyst)
        )
        assert pdf.status_code == 200
        assert pdf.content[:5] == b"%PDF-"

        docx = await client.get(
            f"/api/v1/reports?type={report_type}&format=docx", headers=auth(analyst)
        )
        assert docx.status_code == 200
        assert docx.content[:2] == b"PK"

        xlsx = await client.get(
            f"/api/v1/reports?type={report_type}&format=xlsx", headers=auth(analyst)
        )
        assert xlsx.status_code == 200
        assert xlsx.content[:2] == b"PK"

    # la exportacion queda registrada en bitacora (accion EXPORT)
    admin = await login(client, "admin", "Admin123!")
    audit = (
        await client.get("/api/v1/audit?module=reports&action=EXPORT", headers=auth(admin))
    ).json()
    assert audit["total"] >= 6


async def test_auditoria_visibilidad_por_rol(client):
    viewer = await login(client, "viewer", "Viewer123!")
    admin = await login(client, "admin", "Admin123!")

    viewer_rows = (
        await client.get("/api/v1/audit?page_size=100", headers=auth(viewer))
    ).json()
    assert viewer_rows["total"] >= 1
    assert {row["username"] for row in viewer_rows["items"]} == {"viewer"}

    admin_rows = (await client.get("/api/v1/audit?page_size=100", headers=auth(admin))).json()
    assert {row["username"] for row in admin_rows["items"]} >= {"viewer"}

    # entrada manual (nodo 10 del workflow n8n)
    entry = await client.post(
        "/api/v1/audit",
        json={
            "module": "triage",
            "action": "EXECUTE",
            "username": "n8n",
            "details": {"node": 10},
        },
        headers=auth(admin),
    )
    assert entry.status_code == 201
    assert entry.json()["module"] == "triage"


async def test_usuarios_crud_admin(client):
    admin = await login(client, "admin", "Admin123!")
    resp = await client.post(
        "/api/v1/users",
        json={
            "username": "nuevo",
            "email": "nuevo@example.com",
            "full_name": "Nuevo Usuario",
            "password": "Nuevo123!",
            "role_name": "analyst",
        },
        headers=auth(admin),
    )
    assert resp.status_code == 201, resp.text
    user_id = resp.json()["id"]

    upd = await client.put(
        f"/api/v1/users/{user_id}",
        json={"role_name": "viewer", "is_active": False},
        headers=auth(admin),
    )
    assert upd.status_code == 200
    assert upd.json()["role_name"] == "viewer"
    assert upd.json()["is_active"] is False

    await client.put(f"/api/v1/users/{user_id}", json={"is_active": True}, headers=auth(admin))
    login_resp = await client.post(
        "/api/v1/auth/login/json", json={"username": "nuevo", "password": "Nuevo123!"}
    )
    assert login_resp.status_code == 200
    assert (
        await client.delete(f"/api/v1/users/{user_id}", headers=auth(admin))
    ).status_code == 204


async def test_incidentes(client):
    analyst = await login(client, "analyst", "Analyst123!")
    resp = await client.post(
        "/api/v1/incidents",
        json={"title": "Incidente de prueba", "severity": "alta", "ticket_id": "OST-999"},
        headers=auth(analyst),
    )
    assert resp.status_code == 201, resp.text
    inc_id = resp.json()["id"]

    upd = await client.patch(
        f"/api/v1/incidents/{inc_id}", json={"status": "closed"}, headers=auth(analyst)
    )
    assert upd.status_code == 200
    assert upd.json()["closed_at"] is not None

    listed = (
        await client.get("/api/v1/incidents?status=closed", headers=auth(analyst))
    ).json()
    assert any(i["id"] == inc_id for i in listed["items"])
