"""Enriquecimiento contextual: VirusTotal, AbuseIPDB y GeoIP.

Modo mock (por defecto, `ENRICHMENT_MOCK=true` o sin API key): respuestas
deterministas para que el MVP funcione 100% offline, señaladas con `mock: true`.
"""

import hashlib
import ipaddress

import httpx

from app.config import settings

# --- Intel local (usa datasets públicos ver docs/datasets.md) ---
KNOWN_MALICIOUS_IPS = {
    "185.220.101.1": "Tor exit node asociado a actividad abusiva",
    "45.155.205.233": "Escaneo masivo reportado (abuse) ",
    "194.26.229.11": "Fuerza bruta SSH reportada",
    "91.240.118.172": "C2 de malware reportado",
    "103.149.162.74": "Brute force RDP reportado",
    "193.32.162.229": "Botnet Mirai conocida",
    "23.129.64.212": "Escaneo de puertos reportado",
}

KNOWN_BENIGN_IPS = {
    "8.8.8.8": "Google Public DNS",
    "1.1.1.1": "Cloudflare DNS",
    "9.9.9.9": "Quad9 DNS",
    "151.101.1.69": "Fastly CDN",
}

GEO_DB = {
    "185.220.101.1": ("Germany", "EU", "Frankfurt"),
    "45.155.205.233": ("Russia", "EU", "Moscow"),
    "194.26.229.11": ("Netherlands", "EU", "Amsterdam"),
    "91.240.118.172": ("Ukraine", "EU", "Kyiv"),
    "103.149.162.74": ("Vietnam", "APAC", "Hanoi"),
    "193.32.162.229": ("China", "APAC", "Beijing"),
    "23.129.64.212": ("United States", "AMER", "New York"),
    "8.8.8.8": ("United States", "AMER", "Mountain View"),
    "1.1.1.1": ("Australia", "APAC", "Sydney"),
    "9.9.9.9": ("United States", "AMER", "Berkeley"),
    "151.101.1.69": ("United States", "AMER", "San Francisco"),
}


def _stable_score(key: str, salt: str) -> int:
    digest = hashlib.sha256(f"{salt}:{key}".encode()).hexdigest()
    return int(digest[:6], 16) % 101


def _is_private(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        return False


def _mock_virustotal(ioc: str) -> dict:
    if ioc in KNOWN_MALICIOUS_IPS:
        score, detections = 78, 14
    elif ioc in KNOWN_BENIGN_IPS:
        score, detections = 2, 0
    else:
        score, detections = _stable_score(ioc, "vt") // 3, 0
    return {
        "ioc": ioc,
        "malicious_detections": detections,
        "suspicious_detections": 1 if 20 <= score < 50 else 0,
        "reputation_score": score,
        "report_url": f"https://www.virustotal.com/gui/ip-address/{ioc}",
        "mock": True,
    }


def _mock_abuseipdb(ip: str) -> dict:
    if ip in KNOWN_MALICIOUS_IPS:
        confidence, abuse_score = 100, 92
    elif ip in KNOWN_BENIGN_IPS or _is_private(ip):
        confidence, abuse_score = 85, 0
    else:
        abuse_score = _stable_score(ip, "abuse") // 4
        confidence = 60 + (_stable_score(ip, "conf") % 30)
    return {
        "ip": ip,
        "abuse_confidence_score": abuse_score,
        "total_reports": abuse_score * 3 if abuse_score else 0,
        "country_code": GEO_DB.get(ip, ("Unknown",))[0][:2].upper() if ip in GEO_DB else "ZZ",
        "isp": "Mock ISP (modo simulado)",
        "usage_type": "COMMUNITY",
        "mock": True,
    }


def _mock_geoip(ip: str) -> dict:
    if _is_private(ip):
        return {"ip": ip, "country": "Private", "region": "LAN", "city": "LAN", "is_private": True, "mock": True}
    country, continent, city = GEO_DB.get(ip, ("Unknown", "Unknown", "Unknown"))
    return {"ip": ip, "country": country, "continent": continent, "city": city, "is_private": False, "mock": True}


def use_mock(kind: str) -> bool:
    if settings.enrichment_mock:
        return True
    if kind == "virustotal" and not settings.virustotal_api_key:
        return True
    if kind == "abuseipdb" and not settings.abuseipdb_api_key:
        return True
    return False


async def _http_get(url: str, headers: dict, params: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers=headers, params=params)
        resp.raise_for_status()
        return resp.json()


async def virustotal_lookup(ioc: str) -> dict:
    if use_mock("virustotal"):
        return _mock_virustotal(ioc)
    if any(c.isdigit() for c in ioc) and "." in ioc:
        url = f"https://www.virustotal.com/api/v3/ip_addresses/{ioc}"
    else:
        url = f"https://www.virustotal.com/api/v3/files/{ioc}"
    data = await _http_get(url, headers={"x-apikey": settings.virustotal_api_key})
    attrs = data.get("data", {}).get("attributes", {})
    stats = attrs.get("last_analysis_stats", {})
    return {
        "ioc": ioc,
        "malicious_detections": stats.get("malicious", 0),
        "suspicious_detections": stats.get("suspicious", 0),
        "reputation_score": attrs.get("reputation", 0),
        "report_url": f"https://www.virustotal.com/gui/ip-address/{ioc}",
        "mock": False,
    }


async def abuseipdb_lookup(ip: str) -> dict:
    if use_mock("abuseipdb"):
        return _mock_abuseipdb(ip)
    data = await _http_get(
        "https://api.abuseipdb.com/api/v2/check",
        headers={"Key": settings.abuseipdb_api_key, "Accept": "application/json"},
        params={"ipAddress": ip, "maxAgeInDays": 90},
    )
    rep = data.get("data", {})
    return {
        "ip": ip,
        "abuse_confidence_score": rep.get("abuseConfidenceScore", 0),
        "total_reports": rep.get("totalReports", 0),
        "country_code": rep.get("countryCode", "ZZ"),
        "isp": rep.get("isp", ""),
        "usage_type": rep.get("usageType", ""),
        "mock": False,
    }


def geoip_lookup(ip: str) -> dict:
    return _mock_geoip(ip)


async def enrich_ip(ip: str, tools: list[str] | None = None) -> dict:
    tools = tools or ["virustotal", "abuseipdb", "geoip"]
    out: dict = {}
    for tool in tools:
        try:
            if tool == "virustotal":
                out[tool] = await virustotal_lookup(ip)
            elif tool == "abuseipdb":
                out[tool] = await abuseipdb_lookup(ip)
            elif tool == "geoip":
                out[tool] = geoip_lookup(ip)
        except Exception as exc:  # noqa: BLE001 - enriquecimiento nunca debe tumbar el triaje
            out[tool] = {"error": str(exc), "tool": tool}
    return out
