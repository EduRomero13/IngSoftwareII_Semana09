"""Contrato del workflow n8n: estructura, versiones, seguridad y rutas de la API.

No ejecuta n8n: valida el JSON exportado contra las reglas del proyecto y contra
las versiones de nodo de n8n 2.45.5.
"""

import json
import re
from collections import deque
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = ROOT / "n8n" / "workflows" / "soc_lite_triage.json"
COMPOSE_PATH = ROOT / "docker-compose.yml"

UUID4 = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)

# typeVersion validados contra n8n@2.45.5 (n8n-nodes-base 2.15.1).
PINNED_VERSIONS = {
    "n8n-nodes-base.webhook": 2.2,
    "n8n-nodes-base.code": 2,
    "n8n-nodes-base.if": 2.4,
    "n8n-nodes-base.httpRequest": 4.5,
    "n8n-nodes-base.switch": 3.5,
    "n8n-nodes-base.slack": 2.7,
    "n8n-nodes-base.noOp": 1,
    "n8n-nodes-base.stickyNote": 1,
}

HTTP_NODE = "n8n-nodes-base.httpRequest"


@pytest.fixture(scope="module")
def workflow() -> dict:
    return json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def nodes(workflow) -> dict[str, dict]:
    return {node["name"]: node for node in workflow["nodes"]}


def _targets(workflow: dict) -> dict[str, list[str]]:
    graph: dict[str, list[str]] = {}
    for source, outputs in workflow["connections"].items():
        graph[source] = [
            edge["node"]
            for output in outputs.get("main", [])
            for edge in output
        ]
    return graph


def test_workflow_es_json_valido_y_exportable(workflow):
    assert workflow["id"] == "SocLiteTriage001"
    assert len(workflow["id"]) == 16
    assert workflow["name"].startswith("SOC-Lite")
    assert workflow["settings"]["executionOrder"] == "v1"
    assert workflow["settings"]["timezone"] == "America/Lima"


def test_nodos_tienen_uuid_y_nombre_unico(workflow):
    ids = [node["id"] for node in workflow["nodes"]]
    names = [node["name"] for node in workflow["nodes"]]
    assert len(ids) == len(set(ids))
    assert len(names) == len(set(names))
    for node_id in ids:
        assert UUID4.match(node_id), node_id


def test_versiones_de_nodo_pinneadas(nodes):
    for node in nodes.values():
        assert node["type"] in PINNED_VERSIONS, node["type"]
        assert node["typeVersion"] == PINNED_VERSIONS[node["type"]], node["name"]


def test_no_hay_nodos_postgres_ni_sql(workflow):
    dump = json.dumps(workflow).upper()
    assert "n8n-nodes-base.postgres" not in json.dumps(workflow)
    for sql in ("INSERT INTO", "UPDATE ", "DELETE FROM", "CREATE TABLE"):
        assert sql not in dump


def test_no_hay_credenciales_ni_secretos_versionados(workflow):
    dump = json.dumps(workflow)
    for forbidden in ("REEMPLAZAR", "soclite-webhook-token", "xoxb-", "eyJhbGciOi"):
        assert forbidden not in dump
    for node in workflow["nodes"]:
        assert "credentials" not in node


def test_conexiones_apuntan_a_nodos_existentes(workflow, nodes):
    for source, outputs in workflow["connections"].items():
        assert source in nodes
        for output in outputs.get("main", []):
            for edge in output:
                assert edge["node"] in nodes
                assert edge["type"] == "main"
                assert edge["index"] == 0


def test_todos_los_nodos_operativos_son_alcanzables(workflow, nodes):
    graph = _targets(workflow)
    start = "1. Webhook alertas Wazuh/OPNsense"
    seen = {start}
    queue = deque([start])
    while queue:
        for target in graph.get(queue.popleft(), []):
            if target not in seen:
                seen.add(target)
                queue.append(target)
    operational = {
        name
        for name, node in nodes.items()
        if node["type"] != "n8n-nodes-base.stickyNote"
    }
    assert operational <= seen


def test_webhook_configurado_para_wazuh(nodes):
    webhook = nodes["1. Webhook alertas Wazuh/OPNsense"]["parameters"]
    assert webhook["httpMethod"] == "POST"
    assert webhook["path"] == "soc-alert"
    assert webhook["authentication"] == "headerAuth"
    assert webhook["responseMode"] == "onReceived"


def test_normalizacion_cubre_campos_de_alerta(nodes):
    code = nodes["2. Normalizar alerta"]["parameters"]["jsCode"]
    for key in ("severity", "title", "rule_id", "src_ip", "dst_ip", "raw_payload", "is_valid"):
        assert key in code
    assert "rule.description" in code
    assert "severityMap" in code


def test_if_valida_alerta_normalizada(nodes):
    conditions = nodes["3. IF alerta valida"]["parameters"]["conditions"]
    assert conditions["combinator"] == "and"
    assert conditions["options"]["version"] == 2
    assert "is_valid" in conditions["conditions"][0]["leftValue"]
    assert conditions["conditions"][0]["operator"]["type"] == "boolean"


def test_http_ingesta_usa_webhook_token(nodes):
    params = nodes["4. HTTP ingesta API"]["parameters"]
    assert params["url"].endswith("/api/v1/alerts/webhook")
    headers = {
        h["name"]: h["value"] for h in params["headerParameters"]["parameters"]
    }
    assert "X-Webhook-Token" in headers
    assert "$env.SOC_WEBHOOK_TOKEN" in headers["X-Webhook-Token"]
    assert "raw_payload" in params["jsonBody"]


def test_http_login_usa_variables_de_entorno(nodes):
    params = nodes["5. HTTP login servicio"]["parameters"]
    assert params["url"].endswith("/api/v1/auth/login/json")
    assert "$env.SOC_API_USER" in params["jsonBody"]
    assert "$env.SOC_API_PASSWORD" in params["jsonBody"]


def test_http_triaje_usa_id_y_jwt(nodes):
    params = nodes["6. HTTP ejecuta triaje"]["parameters"]
    assert "/api/v1/triage/" in params["url"]
    assert "4. HTTP ingesta API" in params["url"]
    headers = {
        h["name"]: h["value"] for h in params["headerParameters"]["parameters"]
    }
    assert headers["Authorization"].startswith("=Bearer")
    assert "5. HTTP login servicio" in headers["Authorization"]
    assert "access_token" in headers["Authorization"]


def test_switch_enruta_alta_media_y_baja(workflow, nodes):
    switch = nodes["7. Switch severidad"]["parameters"]
    rules = switch["rules"]["values"]
    assert [rule["outputKey"] for rule in rules] == ["alta", "media"]
    assert rules[0]["conditions"]["conditions"][0]["rightValue"] == "alta"
    assert rules[1]["conditions"]["conditions"][0]["rightValue"] == "media"
    assert switch["options"]["fallbackOutput"] == "extra"
    assert switch["options"]["renameFallbackOutput"] == "baja"

    outputs = workflow["connections"]["7. Switch severidad"]["main"]
    assert len(outputs) == 3
    assert outputs[0][0]["node"] == "8. Slack notifica alta"
    assert outputs[1][0]["node"] == "10. HTTP ticket osTicket (media)"
    assert outputs[2][0]["node"] == "11. Fin rama baja (sin notificacion)"


def test_slack_solo_recibe_severidad_alta(workflow, nodes):
    targets = _targets(workflow)
    sources = [source for source, names in targets.items() if "8. Slack notifica alta" in names]
    assert sources == ["7. Switch severidad"]
    slack = nodes["8. Slack notifica alta"]
    assert slack["parameters"]["channelId"]["value"] == "={{ $env.SLACK_CHANNEL }}"
    assert slack["parameters"]["messageType"] == "text"
    assert targets["8. Slack notifica alta"] == ["9. HTTP ticket osTicket (alta)"]


def test_osticket_recibe_alta_y_media(nodes):
    for name in ("9. HTTP ticket osTicket (alta)", "10. HTTP ticket osTicket (media)"):
        params = nodes[name]["parameters"]
        assert params["url"] == "={{ $env.OSTICKET_URL }}"
        headers = {h["name"]: h["value"] for h in params["headerParameters"]["parameters"]}
        assert headers["X-API-Key"] == "={{ $env.OSTICKET_API_KEY }}"
        assert "$('6. HTTP ejecuta triaje')" in params["jsonBody"]


def test_reintentos_en_la_raiz_del_nodo(workflow, nodes):
    for node in workflow["nodes"]:
        if node["type"] != HTTP_NODE:
            continue
        assert "retry" not in node["parameters"].get("options", {})
        if node.get("retryOnFail"):
            assert node["maxTries"] >= 2
            assert node["waitBetweenTries"] >= 1000


def test_docker_compose_pinnea_n8n_y_no_publica_puertos():
    compose = COMPOSE_PATH.read_text(encoding="utf-8")
    assert "n8nio/n8n:2.45.5" in compose
    assert "n8nio/n8n:latest" not in compose
    assert "5678:5678" not in compose
    for env in ("N8N_ENCRYPTION_KEY", "N8N_PROXY_HOPS", "N8N_WEBHOOK_URL", "SOC_API_URL"):
        assert env in compose
