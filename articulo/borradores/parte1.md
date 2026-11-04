# Clasificador automático de alertas SOC para PYMES basado en un agente LLM local y enriquecimiento contextual: un estudio de evaluación reproducible

**Automatic SOC alert classification for SMEs based on a local LLM agent and contextual enrichment: a reproducible evaluation study**

[Author 1]^a, [Author 2]^b

^a Escuela Profesional de Ingeniería de Software, Facultad de Ingeniería, Universidad [Nombre], [Ciudad], [País]. Correo: [correo@universidad.edu]

^b [Afiliación], [Ciudad], [País]. Correo: [correo@institucion.edu]

**Autor de correspondencia:** [Nombre completo], [dirección postal], [correo electrónico].

**Recibido:** [fecha] · **Aceptado:** [fecha] · **Publicado:** [fecha]

**Cómo citar:** [Autor 1], [Autor 2]. (2026). Clasificador automático de alertas SOC para PYMES basado en un agente LLM local y enriquecimiento contextual: un estudio de evaluación reproducible. *[Revista]*, *[volumen]*([número]), [páginas]. https://doi.org/[DOI]

---

## Resumen

**Contexto.** Las pequeñas y medianas empresas (PYMES) enfrentan volúmenes crecientes de alertas de seguridad con equipos reducidos y presupuestos limitados. Los centros de operaciones de seguridad (SOC) tradicionales dependen de reglas y de revisión manual, lo que produce fatiga de alertas, falsos positivos y tiempos de respuesta elevados. Los modelos de lenguaje grandes (LLM) ofrecen razonamiento sobre texto no estructurado, pero su adopción en PYMES está limitada por costos, privacidad, latencia, calibración y falta de evaluaciones reproducibles.

**Objetivo.** Evaluar, en un escenario simulado y reproducible, un clasificador automático de alertas SOC que combina un agente LLM local, enriquecimiento contextual y una política de decisión calibrada, y comparar su rendimiento, calibración, robustez e impacto operacional con enfoques heurísticos y modelos supervisados.

**Método.** Se construyó un banco de pruebas de 12.480 alertas derivadas de CICIDS2017, UNSW-NB15, plantillas de reglas de Wazuh/OPNsense y negativos duros, con etiquetas operacionales de verdadero positivo (VP), falso positivo (FP) y sospechoso (SUS). Se compararon siete sistemas —heurístico, regresión logística, máquina de vectores de soporte, bosque aleatorio, XGBoost, BETO ajustado y SOC-Lite— mediante una partición estratificada por grupos 70/10/20, validación cruzada de hiperparámetros, *bootstrap* estratificado (2.000 réplicas), pruebas de McNemar y análisis de ablación. SOC-Lite integra llama3.1 8B mediante Ollama y LangChain, consultas a VirusTotal, AbuseIPDB, GeoIP e inteligencia local, salida estructurada y calibración por temperatura.

**Resultados.** En el conjunto de prueba (2.496 alertas), SOC-Lite obtuvo una macro-F1 de 0,891 (IC 95 %: 0,881–0,901), exactitud de 0,907, PR-AUC de 0,931, Brier de 0,088 y ECE de 0,042, con una latencia mediana de 3,84 s. Superó a XGBoost (Δ macro-F1 = +0,062; IC 95 %: 0,051–0,073) y a BETO ajustado (+0,044; 0,033–0,055), con *p* < 0,001 en ambas comparaciones. La ablación mostró que la salida estructurada (−0,074), la inteligencia local (−0,030) y VirusTotal (−0,023) fueron los componentes más relevantes. El sistema redujo el esfuerzo estimado a 7,2 horas de analista por 1.000 alertas y elevó la precisión de escalamiento al 94,1 %, con una tasa de degradación controlada del 1,2 %.

**Conclusiones.** Un agente LLM local, combinado con enriquecimiento contextual, salida estructurada y calibración, puede mejorar el triaje de alertas en PYMES sin enviar datos a servicios externos de inferencia. No obstante, los resultados provienen de un escenario simulado y calibrado, no de un despliegue productivo; la generalización requiere validación prospectiva, evaluación adversarial y monitoreo de deriva. El estudio aporta un artefacto, un protocolo de evaluación y evidencia cuantitativa sobre el valor y los límites de cada componente.

**Palabras clave:** triaje de alertas; centro de operaciones de seguridad; modelos de lenguaje grandes; agentes locales; enriquecimiento contextual; calibración de la confianza; PYMES.

**Keywords:** alert triage; security operations center; large language models; local agents; contextual enrichment; confidence calibration; SMEs.

---

## 1. Introducción

### 1.1. Contexto: la presión operativa sobre las PYMES

La digitalización de las PYMES ha ampliado su superficie de ataque al mismo tiempo que ha reducido la proporción de recursos dedicados a seguridad. Un incidente de *ransomware* o un compromiso de credenciales puede interrumpir la operación, exponer datos personales y activar obligaciones regulatorias. Marcos de referencia como el *NIST Cybersecurity Framework* 2.0 (NIST, 2024) y la norma ISO/IEC 27001:2022 (ISO/IEC, 2022) subrayan la necesidad de detectar, responder y aprender de los incidentes, pero no resuelven por sí mismos el cuello de botella operativo: convertir una señal técnica en una decisión accionable.

En un SOC, ese proceso se denomina triaje. Consiste en determinar si una alerta es un verdadero positivo, un falso positivo o un caso que requiere más evidencia, y en asignarle una severidad y una acción. La literatura clásica sobre detección de intrusiones ya advertía que el rendimiento en laboratorio no se traduce automáticamente en utilidad operacional debido a la asimetría de costos y a la baja prevalencia de ataques (Sommer & Paxson, 2010). En PYMES, el problema se agrava porque el mismo analista que revisa alertas también administra infraestructura, atiende incidentes y documenta controles. La fatiga de alertas no es solo un fenómeno cognitivo: es una falla de diseño del sistema de decisión.

Los SOC modernos combinan reglas de detección, correlación y enriquecimiento. Wazuh y OPNsense, por ejemplo, generan alertas con metadatos de regla, activo, dirección IP y severidad. Sin embargo, la alerta cruda carece de contexto: no sabe si la IP ya fue reportada como maliciosa, si el activo es crítico, si el comportamiento es habitual o si la regla tiene un historial de falsos positivos. El enriquecimiento contextual reduce esa incertidumbre, pero añade latencia, dependencias externas y nuevos modos de fallo. La pregunta de ingeniería es cómo integrar ese contexto en una decisión trazable, calibrada y económica para una PYME.

### 1.2. Estado del arte: de la detección al razonamiento asistido

La investigación sobre detección de intrusiones ha producido una base metodológica sólida. Los conjuntos de datos CICIDS2017 (Sharafaldin et al., 2018) y UNSW-NB15 (Moustafa & Slay, 2015) permitieron comparar clasificadores supervisados con características de flujo y de paquete. Los modelos de árboles y de *boosting* —bosques aleatorios (Breiman, 2001) y XGBoost (Chen & Guestrin, 2016)— se convirtieron en referencias por su rendimiento y su bajo costo de inferencia. Las máquinas de vectores de soporte (Cortes & Vapnik, 1995) y la regresión logística siguen siendo líneas base interpretables. En procesamiento de lenguaje natural, los *transformers* (Vaswani et al., 2017) y BERT (Devlin et al., 2019) habilitaron representaciones contextuales; BETO (Cañete et al., 2020) extendió ese enfoque al español.

La irrupción de los LLM desplazó el foco desde la clasificación de características hacia el razonamiento sobre evidencia textual. Los modelos de la familia GPT demostraron aprendizaje con pocos ejemplos (Brown et al., 2020), razonamiento en cadena (Wei et al., 2022; Kojima et al., 2023) y uso de herramientas (Yao et al., 2023). La generación aumentada por recuperación (Lewis et al., 2020) mostró cómo incorporar conocimiento externo sin reentrenar el modelo. Estas capacidades son atractivas para el triaje, porque una alerta es, en esencia, un documento breve con metadatos, evidencia y una pregunta de decisión.

La aplicación de LLM a SOC ha comenzado a evaluarse empíricamente. Hasanov et al. (2024) revisaron sistemáticamente la literatura y encontraron predominio de estudios conceptuales, prototipos y evaluaciones de laboratorio, con pocos despliegues medidos en operación. Rieger et al. (2026) evaluaron ocho LLM comerciales y de código abierto sobre 178 alertas etiquetadas manualmente: la mayoría alcanzó una exhaustividad superior al 90 % en clasificación, pero la priorización mostró baja precisión y alto ruido. Singh et al. (2025) analizaron 3.090 consultas de 45 analistas durante diez meses y concluyeron que los LLM funcionan como ayudas cognitivas que aumentan, más que reemplazan, la experiencia del analista. Nath et al. (2026), a partir de 892 publicaciones de foros, documentaron adopción para tareas de bajo riesgo y desconfianza persistente hacia la autonomía plena. Zhao et al. (2025) propusieron un esquema de razonamiento compacto con expertos LoRA y una arquitectura nube-borde, con reducción de latencia frente a cadenas de razonamiento extensas. Habibzadeh et al. (2025) sintetizaron el campo y señalaron la fragmentación de métricas, la falta de comparaciones justas y la escasez de artefactos reproducibles.

En paralelo, la literatura sobre sistemas de aprendizaje automático en producción advierte que el rendimiento predictivo es solo una parte del problema. Sculley et al. (2015) describieron la deuda técnica oculta; Paleyes et al. (2022) sistematizaron los desafíos de despliegue; Breck et al. (2017) propusieron rúbricas de preparación para producción; Mitchell et al. (2019) y Gebru et al. (2021) insistieron en documentar modelos y datos. La calibración de probabilidades (Guo et al., 2017) y las métricas proper scoring como el Brier score (Brier, 1950) son especialmente relevantes cuando la decisión no es solo etiquetar, sino priorizar y automatizar cierres.

### 1.3. Brecha de conocimiento

Aunque el triaje con LLM se ha estudiado mediante prototipos y evaluaciones exploratorias, persiste sin resolver la pregunta de si un agente local, de bajo costo y con enriquecimiento contextual puede alcanzar un rendimiento operacionalmente útil en el contexto de una PYME, manteniendo calibración, trazabilidad y una degradación controlada. Esta limitación importa por tres razones. Primera, la mayoría de las evaluaciones utiliza modelos comerciales en la nube, lo que plantea riesgos de privacidad y costos variables para organizaciones con datos sensibles. Segunda, los estudios suelen reportar exactitud o exhaustividad sin intervalos de confianza, sin análisis de ablación y sin métricas de calibración, lo que impide atribuir las mejoras a componentes específicos. Tercera, la evidencia sobre el impacto operacional —horas de analista, precisión de escalamiento, cobertura de autocierre y costo por 1.000 alertas— es escasa y difícil de comparar.

Este estudio aborda la brecha mediante un artefacto (SOC-Lite) y un protocolo de evaluación reproducible que combina un agente LLM local, enriquecimiento contextual, salida estructurada y una política de decisión calibrada. El escenario es simulado y calibrado con el artefacto; no se presenta como un despliegue productivo. Esa decisión permite controlar la composición del banco de pruebas, auditar las etiquetas y repetir el análisis, a costa de una validez externa limitada que se discute explícitamente.
