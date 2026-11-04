### 1.4. Propósito, preguntas de investigación y alcance

El propósito del estudio es evaluar si un clasificador de alertas SOC basado en un agente LLM local y enriquecimiento contextual puede superar a líneas base heurísticas y supervisadas en un escenario reproducible, y determinar qué componentes explican esa mejora. El alcance se limita a alertas individuales de seguridad, con etiquetas operacionales de tres clases (VP, FP y SUS) y severidad de tres niveles (alta, media y baja). No se abordan la respuesta automática completa, la remediación ni la atribución de adversarios.

El estudio responde cuatro preguntas:

- **PI1. Rendimiento global.** ¿En qué medida SOC-Lite mejora la macro-F1, la exactitud, la PR-AUC y la calibración respecto de un heurístico y de modelos supervisados (regresión logística, SVM, bosque aleatorio, XGBoost y BETO ajustado) en el conjunto de prueba?
- **PI2. Contribución de componentes.** ¿Qué aportan el enriquecimiento con VirusTotal, AbuseIPDB, GeoIP y inteligencia local, la salida estructurada y la calibración de la confianza al rendimiento final?
- **PI3. Severidad y decisión.** ¿La clasificación de severidad y la política de decisión permiten priorizar la cola de escalamiento sin aumentar de forma inaceptable los falsos negativos?
- **PI4. Robustez e impacto operacional.** ¿Cómo se degrada el sistema ante ruido de etiquetas, deriva temporal, variaciones de *prompt* y temperatura, y qué efecto tiene sobre horas de analista, costo y cumplimiento de SLA?

La hipótesis principal es que el enriquecimiento contextual y la salida estructurada producen una mejora sustancial y atribuible sobre las líneas base, mientras que la calibración mejora la utilidad de la decisión más que la discriminación. No se plantea una hipótesis causal sobre el despliegue real: el diseño es una evaluación experimental sobre un banco de pruebas simulado.

### 1.5. Contribuciones

El estudio realiza cinco contribuciones verificables:

1. **Artefacto desplegable.** SOC-Lite, una arquitectura de referencia para PYMES que integra Wazuh/OPNsense, n8n, FastAPI, PostgreSQL, un agente LangChain con llama3.1 8B local, enriquecimiento contextual y una interfaz de monitoreo. El artefacto prioriza inferencia local, trazabilidad y degradación controlada.
2. **Banco de pruebas reproducible.** Un conjunto de 12.480 alertas construido a partir de CICIDS2017, UNSW-NB15, plantillas de reglas de Wazuh/OPNsense y negativos duros, con etiquetas operacionales auditadas y una partición por grupos que reduce la fuga de información.
3. **Evaluación comparativa rigurosa.** Siete sistemas evaluados sobre el mismo conjunto de prueba, con intervalos de confianza *bootstrap*, tamaños de efecto, pruebas de McNemar, análisis de calibración y métricas operacionales.
4. **Análisis de atribución y robustez.** Ablación de cinco componentes y pruebas de sensibilidad a ruido de etiquetas, deriva temporal, paráfrasis del *prompt*, temperatura y tamaño del modelo.
5. **Principios de diseño para PYMES.** Un conjunto de decisiones justificadas —inferencia local, salida estructurada, abstención explícita, calibración y *fallback* determinista— que pueden transferirse a otros despliegues con restricciones similares.

### 1.6. Organización del artículo

La Sección 2 sintetiza los trabajos relacionados y precisa la brecha. La Sección 3 describe el artefacto, el banco de pruebas, el protocolo experimental, las métricas y las consideraciones éticas. La Sección 4 presenta los resultados en el orden de las preguntas de investigación. La Sección 5 discute implicaciones, validez y limitaciones. La Sección 6 responde al objetivo y delimita el alcance de las conclusiones. Los apéndices documentan el *prompt*, la reproducibilidad y la nota de transparencia sobre los datos simulados.

---

## 2. Trabajos relacionados

### 2.1. Detección de intrusiones y triaje: dos problemas distintos

La literatura sobre detección de intrusiones suele evaluar la capacidad de distinguir tráfico malicioso de tráfico benigno. Ese problema es diferente del triaje. Un detector puede tener una AUC alta y, aun así, generar una cola de alertas inmanejable si la prevalencia de ataques es baja y el costo de revisar un falso positivo es alto. Sommer y Paxson (2010) formalizaron esta objeción: las métricas agregadas ocultan la *falacia de la tasa base* y pueden justificar despliegues que no resisten el uso operacional. La consecuencia metodológica es que el triaje debe evaluarse con métricas sensibles a la clase minoritaria y con costos explícitos, no solo con exactitud.

Los conjuntos de datos públicos resolvieron parcialmente el problema de la comparabilidad. CICIDS2017 (Sharafaldin et al., 2018) aportó tráfico etiquetado con ataques modernos y características de flujo; UNSW-NB15 (Moustafa & Slay, 2015) incorporó una taxonomía más amplia de ataques y tráfico normal. Ambos han sido criticados por sesgos de captura, duplicados y deriva temporal, pero siguen siendo útiles para construir escenarios controlados. En este estudio no se usan como *benchmark* de detección, sino como materia prima para generar alertas con texto, metadatos y contexto; esa distinción es importante para interpretar los resultados.

### 2.2. Modelos supervisados y representaciones textuales

Los modelos supervisados ofrecen líneas base fuertes y económicas. Los bosques aleatorios (Breiman, 2001) combinan árboles decorrelacionados y son robustos a escalas heterogéneas; XGBoost (Chen & Guestrin, 2016) optimiza una función de pérdida regularizada y suele dominar tablas de datos estructurados. Las SVM con kernel RBF (Cortes & Vapnik, 1995) modelan fronteras no lineales, y la regresión logística proporciona una referencia interpretable. En texto, los *transformers* (Vaswani et al., 2017) y BERT (Devlin et al., 2019) capturan dependencias contextuales; BETO (Cañete et al., 2020) adapta ese enfoque al español y ha sido utilizado en tareas de clasificación con recursos limitados.

Estos modelos tienen una limitación común para el triaje: dependen de la representación de entrada y no razonan explícitamente sobre evidencia heterogénea. Un XGBoost puede aprender que una IP con historial malicioso eleva la probabilidad de un VP, pero no puede explicar por qué, ni consultar una fuente externa durante la inferencia, ni abstenerse cuando la evidencia es contradictoria. Un LLM, en cambio, puede integrar texto de la alerta, resultados de enriquecimiento y reglas de decisión en una única secuencia de razonamiento, a costa de latencia, variabilidad y riesgo de alucinación (Ji et al., 2023).

### 2.3. LLM en operaciones de seguridad

La revisión sistemática de Hasanov et al. (2024) identificó aplicaciones de LLM en detección de amenazas, análisis de registros, inteligencia de amenazas, respuesta a incidentes y formación. Sin embargo, la mayoría de los trabajos se concentra en pruebas de concepto y no reporta métricas operacionales comparables. Rieger et al. (2026) aportaron una de las evaluaciones más directas: ocho modelos, 178 alertas y dos tareas (clasificación y priorización). Encontraron una tensión relevante: los modelos detectan bien los casos positivos, pero priorizan mal, con precisión baja y ruido elevado. Ese hallazgo es consistente con la idea de que la clasificación binaria y la priorización son tareas distintas, y que esta última exige calibración y contexto organizacional.

Singh et al. (2025) desplazaron la mirada hacia la colaboración humano-IA. Su estudio longitudinal muestra que los analistas usan LLM para interpretar telemetría, resumir hallazgos y mejorar la comunicación técnica, no para delegar decisiones de alto riesgo. Nath et al. (2026) confirmaron esa pauta en foros profesionales: adopción para tareas de bajo riesgo, escepticismo ante la autonomía y preocupación por la verificación. Zhao et al. (2025) propusieron una arquitectura que reduce la latencia mediante razonamiento compacto y expertos LoRA, manteniendo la residencia de datos. Habibzadeh et al. (2025) señalaron que la falta de *benchmarks* comunes y de artefactos abiertos dificulta la acumulación de conocimiento.

La literatura sobre despliegue añade una capa de realismo. Sculley et al. (2015) mostraron que los sistemas de aprendizaje automático acumulan deuda técnica en datos, configuración, dependencias y monitoreo. Paleyes et al. (2022) documentaron fallos de despliegue asociados a cambios de distribución y a la desconexión entre métricas de laboratorio y objetivos de negocio. Breck et al. (2017) propusieron evaluar la preparación para producción con criterios explícitos, y Mitchell et al. (2019) y Gebru et al. (2021) subrayaron la necesidad de documentar limitaciones y procedencia. Este estudio incorpora esas lecciones en el diseño experimental: reporta calibración, degradación, costo y condiciones de fallo, no solo precisión.

### 2.4. Síntesis crítica y brecha

La Tabla 1 sintetiza los trabajos más cercanos y permite observar un patrón. Los estudios de detección aportan datos y métricas, pero no modelan la decisión de triaje. Los estudios de LLM en SOC aportan evidencia cualitativa o exploratoria, pero rara vez comparan componentes, reportan calibración o evalúan el costo operacional. Los estudios de despliegue aportan criterios de producción, pero no un artefacto concreto para PYMES. La intersección —un agente local, calibrado, con enriquecimiento contextual y evaluación reproducible— permanece poco explorada.

**Tabla 1.** *Síntesis de trabajos relacionados y brecha de conocimiento.*

| Estudio y enfoque | Datos y contexto | Método | Hallazgo principal | Limitación y brecha |
|---|---|---|---|---|
| Sommer y Paxson (2010). Crítica a la evaluación de detección | Tráfico de red y literatura de IDS | Análisis conceptual y empírico de tasas base | Las métricas agregadas pueden ocultar un rendimiento operacional insuficiente | No propone un clasificador de triaje ni evalúa LLM |
| Sharafaldin et al. (2018). CICIDS2017 | Cinco días de tráfico etiquetado | Características de flujo y comparación de clasificadores | Un conjunto reproducible permite comparar detectores | No modela contexto organizacional ni priorización |
| Moustafa y Slay (2015). UNSW-NB15 | Tráfico sintético y capturado, múltiples ataques | Características híbridas y evaluación supervisada | Amplía la taxonomía de ataques y tráfico normal | Etiquetas de detección, no de disposición operacional |
| Hasanov et al. (2024). Revisión sistemática | Literatura de LLM en ciberseguridad | Revisión sistemática | Predominan prototipos y evaluaciones de laboratorio | Pocos despliegues medidos y métricas heterogéneas |
| Rieger et al. (2026). Clasificación y priorización con LLM | 178 alertas etiquetadas manualmente | Ocho LLM, clasificación binaria y priorización | Alta exhaustividad, baja precisión de priorización | Muestra pequeña, modelos en la nube, sin ablación ni calibración |
| Singh et al. (2025). Colaboración humano-IA | 3.090 consultas de 45 analistas en 10 meses | Estudio longitudinal y análisis de consultas | Los LLM aumentan la experticia, no la reemplazan | No evalúa un clasificador automático end-to-end |
| Nath et al. (2026). Adopción y percepciones | 892 publicaciones de foros (2022–2025) | Análisis mixto de contenido | Adopción para bajo riesgo y escepticismo ante autonomía | Sin medición cuantitativa de rendimiento |
| Zhao et al. (2025). Razonamiento compacto | Alertas SOC y arquitectura nube-borde | Expertos LoRA y razonamiento denso | Menor latencia que cadenas extensas, con residencia de datos | No reporta costo operacional ni calibración en PYMES |
| Habibzadeh et al. (2025). Revisión de LLM en SOC | Literatura 2022–2025 | Revisión comprehensiva | Fragmentación de métricas y falta de artefactos | No ofrece un protocolo experimental replicable |
| **Este estudio (SOC-Lite)** | **12.480 alertas simuladas y etiquetadas** | **Agente local + enriquecimiento + calibración + ablación** | **Mejora atribuible y costo operacional medido** | **Escenario simulado; validez externa limitada** |

*Nota.* VP = verdadero positivo; FP = falso positivo; SUS = sospechoso. La columna “Limitación y brecha” identifica por qué cada trabajo no responde a la pregunta de este estudio. Elaboración propia a partir de las fuentes citadas.

La Tabla 1 muestra que la brecha no es la ausencia de LLM en SOC, sino la ausencia de una evaluación que conecte el rendimiento del modelo con la decisión operacional y con el costo. Este estudio no pretende demostrar que los LLM son superiores en abstracto; pretende medir en qué condiciones un agente local aporta valor y cuándo ese valor depende de componentes auxiliares. Esa es la contribución que se desarrolla a continuación.
