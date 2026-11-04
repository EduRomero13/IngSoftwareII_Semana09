## 3. Métodos

### 3.1. Enfoque y diseño

El estudio adopta un diseño cuantitativo, experimental y de investigación en ciencia del diseño (*design science research*). La elección se justifica por el objetivo: no se busca describir una práctica existente, sino construir y evaluar un artefacto que resuelva un problema operacional delimitado. El artefacto es el sistema SOC-Lite; la evaluación es un experimento controlado sobre un banco de pruebas reproducible. La unidad de análisis es la alerta individual; la unidad de decisión es el par (veredicto, severidad) producido por el sistema.

El escenario es simulado. Las alertas se generan a partir de datos públicos, plantillas de reglas y negativos duros, y las etiquetas se asignan mediante un protocolo de adjudicación documentado. Los valores numéricos reportados corresponden a una ejecución de referencia del artefacto sobre ese banco de pruebas; no provienen de un despliegue productivo. Esta decisión permite controlar la composición, auditar las etiquetas y repetir el análisis, pero limita la validez externa. La Sección 5.4 discute ese trade-off con detalle.

El periodo de observación simulado abarca alertas con marcas de tiempo distribuidas en 18 meses. Esa distribución permite construir un escenario de deriva temporal: el conjunto de prueba incluye los últimos tres meses, de modo que las variantes de robustez puedan evaluar la degradación ante cambios de distribución. No se utilizan datos personales reales; las direcciones IP, nombres de activos y identificadores se anonimizan o se generan de forma sintética.

### 3.2. Artefacto SOC-Lite: arquitectura y flujo de triaje

SOC-Lite es una arquitectura de referencia para PYMES que integra componentes de código abierto y un agente LLM local. La Figura 1 resume el flujo. Las alertas crudas provienen de Wazuh y OPNsense. n8n 2.45.5 actúa como orquestador: recibe el evento, normaliza el esquema, obtiene un token de servicio y llama al *webhook* de FastAPI. La API valida el token `X-Webhook-Token`, aplica deduplicación mediante SHA-256 y persiste la alerta en PostgreSQL 16. Después, el servicio de triaje recupera la alerta, ejecuta el enriquecimiento contextual, invoca al agente y aplica la política de decisión. El resultado se guarda en `triage_results` y `enrichment_data`, y se registra la operación en `audit_log`. n8n consume el veredicto y enruta según severidad: Slack para alertas altas y osTicket para altas y medias. El *dashboard* en React muestra KPIs, tiempo medio de triaje (MTTT), tasa de falsos positivos, distribución por severidad y cola priorizada.

![Figura 1. Arquitectura y flujo de triaje de SOC-Lite.](figuras/figura1_arquitectura.png)

**Figura 1.** *Arquitectura y flujo de triaje de SOC-Lite.* La columna izquierda muestra la ingesta y la orquestación; la columna central, el triaje y la clasificación; la columna derecha, la persistencia y la respuesta. La línea roja punteada delimita la frontera de inferencia local: el modelo llama3.1 8B se ejecuta en el mismo perímetro que los datos y no se envían alertas a APIs externas de LLM. Las APIs de enriquecimiento (VirusTotal, AbuseIPDB, GeoIP) son opcionales y se consultan solo con los indicadores estrictamente necesarios. La línea roja discontinua entre el agente y el *fallback* representa la degradación controlada ante *timeout*, error de esquema o baja confianza. Elaboración propia.

La arquitectura separa deliberadamente tres responsabilidades. La primera es la **ingesta**: normalizar, autenticar y deduplicar. La segunda es el **razonamiento**: enriquecer, invocar al agente y producir una salida estructurada. La tercera es la **decisión**: calibrar la confianza, aplicar umbrales y enrutar. Esta separación permite auditar cada etapa y sustituir componentes sin reentrenar el sistema completo. También permite implementar una degradación controlada: si el agente falla, el servicio no se detiene; recurre a un heurístico determinista y marca el resultado como `fallback`.

El agente se implementa con LangChain y ChatOllama. El modelo base es llama3.1 8B en cuantización Q5_K_M (Meta AI, 2024), de la familia Llama (Touvron et al., 2023), servido por Ollama en el mismo *host*. La salida se valida con un esquema Pydantic que exige siete campos: `verdict` (VP, FP o SUS), `severity` (alta, media o baja), `confidence` (0–1), `rationale` (texto breve), `evidence` (lista de indicadores), `recommended_action` y `needs_human_review` (booleano). Si la salida no cumple el esquema, se reintenta una vez con una instrucción correctiva; si vuelve a fallar, se activa el *fallback*. El Apéndice A reproduce el *prompt* del sistema.

El agente dispone de cuatro herramientas: consulta a VirusTotal para reputación de IP, dominio o hash; consulta a AbuseIPDB para reportes de abuso; resolución GeoIP para país, ASN y tipo de red; y búsqueda en una tabla local de inteligencia de amenazas con indicadores observados en la organización. Las herramientas devuelven JSON y el agente decide cuáles invocar según el tipo de alerta. No se permite la ejecución de código ni el acceso a recursos fuera de las herramientas registradas. Esa restricción reduce la superficie de ataque y facilita la auditoría.

La política de decisión combina el veredicto, la severidad y la confianza calibrada. Se definen tres rutas:

- **Escalamiento inmediato:** veredicto VP con severidad alta, o cualquier alerta con indicador malicioso confirmado en inteligencia local, o activo de criticidad alta con veredicto VP.
- **Autocierre:** veredicto FP con confianza calibrada ≥ 0,75, sin indicadores maliciosos y con activo de criticidad baja o media.
- **Revisión humana:** veredicto SUS, confianza < 0,60, evidencia contradictoria o cualquier caso que no cumpla las condiciones anteriores.

Los umbrales no se optimizaron sobre el conjunto de prueba. Se fijaron sobre el conjunto de validación con una búsqueda en rejilla que maximiza una función de utilidad costosensible: cada VP escalado correctamente suma 1; cada FP autocerrado correctamente suma 0,5; cada VP autocerrado por error resta 5; cada FP escalado por error resta 1. Esa asimetría refleja el costo operacional de un falso negativo y evita que el sistema maximice cobertura a expensas de la seguridad.

### 3.3. Construcción del banco de pruebas

El banco de pruebas contiene 12.480 alertas. La composición busca cubrir tres regímenes: tráfico de red con etiquetas de ataque, alertas de reglas de producción y negativos duros que se parecen a incidentes pero no lo son. La Tabla 2 detalla las fuentes, la distribución de clases y las variables disponibles. La Figura 2 visualiza la composición y la distribución.

Las alertas de CICIDS2017 se generaron a partir de registros de flujo. Para cada flujo se construyó un texto de alerta con una plantilla que resume origen, destino, protocolo, duración, bytes, paquetes, banderas y una descripción de la regla. La etiqueta operacional se derivó del etiquetado original y de dos criterios adicionales: criticidad del activo y evidencia de impacto. Un flujo de ataque dirigido a un activo crítico se etiquetó como VP; un intento bloqueado sin impacto se etiquetó como FP; un flujo ambiguo o con señales contradictorias se etiquetó como SUS. Este último caso es importante porque el triaje real rara vez es binario.

Las alertas de UNSW-NB15 siguieron un procedimiento análogo, con 49 características y una taxonomía más amplia de ataques. Las alertas de Wazuh/OPNsense se generaron a partir de 20 plantillas de reglas representativas (fuerza bruta, escaneo, acceso a recursos, cambios de privilegios, *malware*, exfiltración, entre otras), alineadas con tácticas y técnicas de MITRE ATT&CK (MITRE, 2024). Cada plantilla se instanció con valores sintéticos coherentes y se combinó con metadatos de activo y de red. Los negativos duros se construyeron con actividad administrativa legítima que suele disparar reglas: copias de seguridad, escaneos de vulnerabilidades autorizados, actualizaciones, accesos remotos de soporte y tareas programadas. Estos casos son esenciales para medir falsos positivos, porque un clasificador que solo aprende de ataques evidentes no generaliza al ruido operacional.

![Figura 2. Composición del banco de pruebas y distribución de clases.](figuras/figura2_datos.png)

**Figura 2.** *Composición del banco de pruebas y distribución de clases.* (a) Número de alertas por fuente y clase operacional. (b) Distribución agregada de las tres clases. La partición es 70 % entrenamiento (8.736), 10 % validación (1.248) y 20 % prueba (2.496). Los negativos duros no contienen VP por construcción: su función es introducir actividad benigna con apariencia de incidente. Elaboración propia.

**Tabla 2.** *Composición del banco de pruebas, variables y función de cada fuente.*

| Fuente | Alertas | VP | FP | SUS | Variables principales | Función en el estudio |
|---|---:|---:|---:|---:|---|---|
| CICIDS2017 | 5.760 | 2.304 | 2.880 | 576 | 78 características de flujo, protocolo, bytes, paquetes, banderas, duración | Aportar tráfico de red etiquetado y diversidad de ataques |
| UNSW-NB15 | 2.880 | 1.152 | 1.440 | 288 | 49 características híbridas, categoría de ataque, servicio, estado | Ampliar la taxonomía y reducir el sesgo de una sola captura |
| Wazuh/OPNsense | 2.400 | 720 | 1.440 | 240 | Regla, nivel, activo, IP origen/destino, usuario, hora, criticidad | Reproducir alertas de producción con metadatos realistas |
| Negativos duros | 1.440 | 0 | 624 | 816 | Actividad administrativa, respaldo, escaneo autorizado, soporte | Medir falsos positivos y ambigüedad operacional |
| **Total** | **12.480** | **4.176** | **6.384** | **1.920** | — | — |

*Nota.* VP = verdadero positivo; FP = falso positivo; SUS = sospechoso. Los porcentajes agregados son 33,5 % VP, 51,2 % FP y 15,4 % SUS. La suma de las fuentes coincide con el total. La partición estratificada por grupos produce 8.736 alertas de entrenamiento, 1.248 de validación y 2.496 de prueba; en prueba, la distribución es 835 VP, 1.277 FP y 384 SUS. Elaboración propia.

El texto de las alertas tiene una mediana de 412 tokens (IQR 280–590) y se truncó a 1.024 tokens para el agente. Las alertas de Wazuh/OPNsense incluyen campos semiestructurados; las de CICIDS y UNSW se serializaron como texto con pares clave-valor. Esta heterogeneidad es intencional: el sistema debe funcionar con alertas de distintas fuentes sin un esquema único. La contrapartida es que el agente puede depender de artefactos de plantilla; la Sección 5.4 analiza ese riesgo.

### 3.4. Etiquetado, adjudicación y control de fuga

Las etiquetas operacionales se asignaron con un protocolo de tres pasos. Primero, un etiquetado automático derivado de la fuente y de las reglas de negocio. Segundo, una revisión manual simulada de una muestra estratificada de 2.400 alertas (19,2 % del total) por dos adjudicadores independientes. Tercero, resolución de desacuerdos por un tercer adjudicador. La concordancia entre los dos primeros fue κ de Cohen (1960) = 0,86 (IC 95 %: 0,84–0,88), considerada sustancial. Los desacuerdos se concentraron en alertas de escaneo y en accesos remotos legítimos, lo que confirma que la frontera entre FP y SUS es la más difícil.

La partición se realizó por grupos, no por alertas individuales. Los grupos se definieron por la combinación de familia de plantilla, host de origen y rango de fechas. Así se evita que una misma plantilla o un mismo host aparezca en entrenamiento y prueba, lo que inflaría artificialmente el rendimiento. La partición es estratificada por clase y por fuente, con proporciones 70/10/20. El conjunto de prueba contiene 2.496 alertas y no se utilizó para ajustar hiperparámetros, umbrales ni calibración.

Se aplicaron controles adicionales contra fuga de información: deduplicación exacta y casi duplicada mediante hash y similitud de Jaccard sobre *shingles* de tokens; eliminación de campos que identifican directamente la etiqueta (por ejemplo, nombres de reglas con la palabra “malware”); y verificación de que ninguna alerta de prueba comparte host, plantilla o indicador con una alerta de entrenamiento. El Apéndice B documenta los comandos y las semillas.

### 3.5. Enriquecimiento contextual

El enriquecimiento convierte una alerta en un expediente de evidencia. Se implementaron cuatro fuentes:

- **VirusTotal:** reputación de IP, dominio, URL y hash. Se consulta solo si la alerta contiene un indicador válido. La respuesta se resume en detecciones maliciosas, número de motores, categoría y fecha de último análisis.
- **AbuseIPDB:** reportes de abuso, confianza, país y rango de fechas. Se usa para discriminar entre infraestructura comprometida y servicios legítimos.
- **GeoIP:** país, ciudad, ASN y tipo de red (residencial, empresarial, centros de datos, VPN/Tor). Se usa como señal contextual, nunca como prueba de malicia.
- **Inteligencia local:** tabla de indicadores observados en la organización, con fuente, primera y última observación, y estado (activo, resuelto, falso positivo conocido).

La cobertura no es completa. En el banco de pruebas, VirusTotal respondió para el 78,4 % de las alertas con indicador; AbuseIPDB, para el 71,2 %; GeoIP, para el 96,8 %; y la inteligencia local, para el 22,6 %. La ausencia de respuesta se codifica explícitamente como `unknown`, no como ausencia de malicia. Esa distinción es crucial: un indicador sin reportes no es un indicador limpio. El agente recibe un campo `enrichment_status` por fuente y se le instruye a reducir la confianza cuando la cobertura es baja.

Las consultas se cachean en PostgreSQL durante 24 horas para reducir latencia y costo. En el escenario simulado, las APIs se sustituyen por un *mock* determinista que reproduce respuestas plausibles y mantiene las tasas de cobertura. Esa decisión permite reproducir el experimento sin claves ni cuotas, a costa de no capturar la variabilidad real de las APIs. El Apéndice C lo explicita.
