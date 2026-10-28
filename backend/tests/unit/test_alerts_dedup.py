"""Deduplicación de alertas: hash SHA-256 compartido por API y webhook."""

from app.api.v1.alerts import make_dedup_hash

GOLDEN = "92700f2ce70ba3e003d056470ccaba61a80c2eec6cbd67f30159ac002a1d213c"


def test_hash_es_estable_y_sha256():
    value = make_dedup_hash(
        "wazuh", "2016497", "194.26.229.11", "192.168.1.50", "Alerta C2"
    )
    assert value == GOLDEN
    assert len(value) == 64
    int(value, 16)  # hexadecimal válido


def test_hash_reproducible_entre_llamadas():
    args = ("wazuh", "100101", "193.32.162.229", "192.168.1.60", "Fuerza bruta SSH")
    assert make_dedup_hash(*args) == make_dedup_hash(*args)


def test_hash_cambia_si_cambia_cualquier_campo():
    base = ("wazuh", "100101", "193.32.162.229", "192.168.1.60", "Fuerza bruta SSH")
    variantes = [
        ("opnsense", "100101", "193.32.162.229", "192.168.1.60", "Fuerza bruta SSH"),
        ("wazuh", "100102", "193.32.162.229", "192.168.1.60", "Fuerza bruta SSH"),
        ("wazuh", "100101", "8.8.8.8", "192.168.1.60", "Fuerza bruta SSH"),
        ("wazuh", "100101", "193.32.162.229", "10.0.0.1", "Fuerza bruta SSH"),
        ("wazuh", "100101", "193.32.162.229", "192.168.1.60", "Otro titulo"),
    ]
    hashes = {make_dedup_hash(*v) for v in variantes}
    assert make_dedup_hash(*base) not in hashes
    assert len(hashes) == len(variantes)


def test_hash_admite_campos_opcionales_nulos():
    assert len(make_dedup_hash("wazuh", None, None, None, "Sin IP")) == 64
