### 4.5. Severidad y impacto operacional

La clasificación de severidad fue razonable, pero menos precisa que el veredicto. La exactitud fue 0,861, la macro-F1 0,853 y la QWK 0,782. La QWK es importante porque mide la concordancia más allá del azar y penaliza los errores graves con mayor intensidad que los leves. Un valor de 0,782 indica una concordancia sustancial, aunque deja margen para mejorar la distinción entre severidad media y baja. En la práctica, el sistema es más fiable para decidir “esto requiere atención inmediata” que para asignar el nivel exacto de prioridad.

El impacto operacional se estimó a partir de la política de decisión y de los tiempos medidos. SOC-Lite redujo el esfuerzo a 7,2 horas de analista por 1.000 alertas, frente a 103,3 horas del triaje manual, 24,8 del heurístico, 12,3 de XGBoost y 10,1 de BETO. La reducción frente al manual es de 93,0 %; frente a BETO, de 28,7 %. El costo de tiempo de analista cayó a USD 144 por 1.000 alertas, sin incluir infraestructura. Si se añade el costo estimado de GPU y energía (USD 3,10 por 1.000 alertas), el costo total asciende a USD 147,10, todavía muy por debajo de los USD 2.066 del triaje manual.

La precisión de escalamiento fue 94,1 %, y solo el 5,9 % de la cola escalada correspondió a falsos positivos. La cobertura de autocierre fue 52,7 %, con un error de autocierre de 7,6 %. El MTTT fue 4,2 s y el cumplimiento de SLA, 98,3 %. Estas cifras deben interpretarse con cautela: son el resultado de una simulación calibrada, no de una operación real. Aun así, permiten comparar el perfil de costo y riesgo de cada enfoque. El sistema no elimina al analista; desplaza su esfuerzo desde la clasificación rutinaria hacia la revisión de casos ambiguos y de alto impacto.

### 4.6. Ablación, robustez y frontera operacional

La Tabla 6, panel A, muestra el efecto de eliminar cada componente. La caída más grande se produjo al eliminar la salida estructurada (−0,074), seguida por la inteligencia local (−0,030), VirusTotal (−0,023), AbuseIPDB (−0,019), la calibración (−0,012) y GeoIP (−0,007). El orden es informativo: la estructura de la salida no es un detalle de implementación, sino un mecanismo que obliga al modelo a comprometerse con una etiqueta, una severidad y una evidencia. Sin ella, el parser falla con más frecuencia, se activa el *fallback* y el rendimiento cae.

La inteligencia local aporta más que las APIs externas porque contiene conocimiento específico de la organización: indicadores ya vistos, falsos positivos conocidos y activos críticos. VirusTotal y AbuseIPDB aportan señal externa, pero son más genéricos y tienen cobertura incompleta. GeoIP aporta poco porque el país o el ASN rara vez discriminan por sí solos entre un ataque y una actividad legítima. Esa jerarquía sugiere una regla de diseño para PYMES: priorizar la memoria organizacional sobre la inteligencia externa, y usar esta última como confirmación, no como fundamento.

La calibración merece una aclaración. El *temperature scaling* no cambia el orden de las probabilidades ni la clase argmax; por tanto, no debería alterar la macro-F1 de clasificación pura. La caída de 0,012 en la variante “sin calibración” se debe a la política de decisión: al aplicar umbrales a probabilidades mal calibradas, el sistema autocierra prematuramente alertas que deberían revisarse, y esas etiquetas finales entran en el cálculo end-to-end. La calibración mejora la utilidad de la decisión, no la discriminación del clasificador. Esa distinción es consistente con Guo et al. (2017) y con la literatura sobre *proper scoring rules*.

![Figura 6. Ablación de componentes y frontera operacional.](figuras/figura6_ablacion_operacion.png)

**Figura 6.** *Ablación de componentes y frontera operacional.* (a) Macro-F1 con intervalos de confianza del 95 % para el sistema completo y seis variantes de ablación. La línea punteada vertical marca el rendimiento del sistema completo. (b) Frontera operacional: horas de analista por 1.000 alertas (escala logarítmica) frente a precisión de escalamiento; cada punto se etiqueta con su MTTT. El punto de SOC-Lite se resalta por su mejor combinación de esfuerzo y precisión. Elaboración propia.

La Figura 6, panel B, resume el *trade-off* operacional. El triaje manual tiene la mayor precisión de escalamiento (21,6 % en el escenario, porque la mayor parte de la cola es ruido) y el mayor costo (103,3 horas). El heurístico es barato (24,8 horas) pero escala mal (46,3 %). XGBoost y BETO mejoran la precisión (68,9 % y 73,8 %) con costos intermedios. SOC-Lite alcanza 94,1 % con 7,2 horas, pero su MTTT es mayor (4,2 s) y requiere GPU. La frontera no es un ranking único: la elección depende de la tolerancia al riesgo, del volumen y de la infraestructura disponible.

**Tabla 6.** *Ablación, robustez e impacto operacional.*

| **Panel A. Ablación de componentes (macro-F1)** | Macro-F1 | IC 95 % | Δ vs. completo |
|---|---:|---:|---:|
| Completo | **0,891** | 0,881–0,901 | — |
| Sin VirusTotal | 0,868 | 0,857–0,879 | −0,023 |
| Sin AbuseIPDB | 0,872 | 0,861–0,883 | −0,019 |
| Sin GeoIP | 0,884 | 0,874–0,894 | −0,007 |
| Sin inteligencia local | 0,861 | 0,850–0,872 | −0,030 |
| Sin salida estructurada | 0,817 | 0,804–0,830 | −0,074 |
| Sin calibración | 0,879 | 0,868–0,890 | −0,012 |

| **Panel B. Robustez (macro-F1)** | Condición | Macro-F1 | Nota |
|---|---|---:|---|
| Ruido de etiquetas | 5 % / 10 % / 15 % | 0,881 / 0,862 / 0,841 | Degradación monotónica |
| Deriva temporal | Últimos 3 meses | 0,871 | −0,020 vs. completo |
| Paráfrasis del *prompt* | 5 variantes | 0,889 ± 0,004 | Estable |
| Temperatura | 0,0 / 0,1 / 0,3 / 0,7 | 0,892 / 0,894 / 0,886 / 0,861 | 0,1 es el óptimo |
| Modelo alternativo | Mistral 7B | 0,871 | −0,020; latencia 2,9 s |
| Modelo mayor | Llama 3.1 70B | 0,907 | +0,016; latencia 18,4 s |

| **Panel C. Frontera operacional (por 1.000 alertas)** | Horas de analista | Precisión de escalamiento | MTTT (s) | Costo analista (USD) |
|---|---:|---:|---:|---:|
| Manual | 103,3 | 21,6 % | 2.556 | 2.066 |
| Heurístico | 24,8 | 46,3 % | 1,2 | 496 |
| XGBoost | 12,3 | 68,9 % | 0,8 | 246 |
| BETO | 10,1 | 73,8 % | 0,6 | 202 |
| **SOC-Lite** | **7,2** | **94,1 %** | **4,2** | **144** |

*Nota.* Panel A: cada fila elimina un componente y mantiene el resto igual; los intervalos se calcularon con *bootstrap* estratificado. Panel B: el ruido de etiquetas se inyectó en el conjunto de entrenamiento, no en prueba; la deriva temporal se evaluó entrenando con los primeros 15 meses y probando con los últimos 3; la paráfrasis del *prompt* se evaluó con cinco redacciones equivalentes; la temperatura se varió en el agente. Panel C: el costo incluye solo tiempo de analista a USD 20/h; el costo de infraestructura de SOC-Lite se estima en USD 3,10 adicionales por 1.000 alertas. MTTT = tiempo medio de triaje. Elaboración propia.

La robustez fue aceptable, pero no uniforme. El ruido de etiquetas degradó el rendimiento de forma monotónica: 0,881 con 5 %, 0,862 con 10 % y 0,841 con 15 %. Esa caída es esperable y sugiere que la calidad del etiquetado es un factor crítico en despliegues reales. La deriva temporal redujo la macro-F1 a 0,871, una caída de 0,020 que puede gestionarse con recalibración periódica y monitoreo de distribución. La paráfrasis del *prompt* produjo una variación mínima (0,889 ± 0,004), lo que indica que el rendimiento no depende de una redacción específica. La temperatura de 0,1 fue la mejor; valores altos aumentaron la variabilidad y redujeron la consistencia.

El tamaño del modelo mostró un *trade-off* claro. Llama 3.1 70B mejoró la macro-F1 a 0,907 (+0,016), pero multiplicó la latencia por 4,8 (18,4 s) y habría requerido hardware más costoso. Mistral 7B (Jiang et al., 2023) rindió peor (0,871) con menor latencia (2,9 s). Para una PYME, el modelo de 8B ofrece el mejor equilibrio entre calidad, latencia y costo; el de 70B solo se justifica si el volumen es bajo y la precisión es crítica.

### 4.7. Análisis cualitativo de fallos

Se revisaron manualmente 120 errores del conjunto de prueba para identificar patrones. Cuatro categorías explican la mayoría:

1. **SUS resuelto como FP con confianza alta (41 casos).** Alertas con evidencia mixta —por ejemplo, una IP con reportes antiguos pero tráfico actual benigno— fueron cerradas como falsos positivos. El agente priorizó la ausencia de malicia reciente y subestimó la ambigüedad.
2. **Cobertura de enriquecimiento incompleta (29 casos).** Alertas sin respuesta de VirusTotal o AbuseIPDB fueron tratadas como si la ausencia de reportes implicara limpieza. El *prompt* instruye a reducir la confianza, pero el modelo no siempre lo hizo.
3. **Plantillas novedosas (27 casos).** Alertas de reglas poco representadas en entrenamiento fueron clasificadas con exceso de confianza. El agente generalizó desde patrones superficiales, como el nombre de la regla o el puerto.
4. **Texto truncado (23 casos).** Alertas largas perdieron evidencia relevante al truncarse a 1.024 tokens. En esos casos, el veredicto se basó en la parte inicial del texto, que a veces contenía solo metadatos.

Estos patrones no invalidan el resultado, pero delimitan sus condiciones de uso. El sistema es más fiable cuando la cobertura de enriquecimiento es alta, la plantilla es conocida y el texto cabe en la ventana de contexto. En un despliegue real, conviene marcar esos casos para revisión humana y monitorear su frecuencia. También conviene evaluar la resistencia a inyección de *prompt*, que no se abordó en este estudio y que es una amenaza relevante cuando el texto de la alerta puede ser controlado por un adversario.

---

## 5. Discusión

### 5.1. Respuesta principal

La respuesta a la pregunta de investigación es condicional pero afirmativa: en el escenario evaluado, un agente LLM local con enriquecimiento contextual, salida estructurada y calibración mejora el triaje de alertas SOC frente a líneas base heurísticas y supervisadas, con un costo operacional menor y una latencia compatible con un flujo asíncrono de PYME. La mejora no proviene del LLM por sí solo, sino de la combinación de razonamiento sobre evidencia, memoria organizacional y una política de decisión calibrada. El sistema no es autónomo ni sustituye al analista; es una capa de priorización y reducción de ruido.

La magnitud de la mejora es moderada en términos absolutos (+0,062 sobre XGBoost, +0,044 sobre BETO) y grande en términos operacionales (7,2 vs. 12,3 horas por 1.000 alertas; 94,1 % vs. 68,9 % de precisión de escalamiento). Esa discrepancia entre métricas de clasificación y métricas operacionales es una lección central: una mejora de cuatro a seis puntos de macro-F1 puede traducirse en una reducción sustancial de la cola de revisión si se concentra en los casos correctos. También explica por qué la evaluación debe incluir costo y calibración, no solo exactitud.

### 5.2. Comparación con la literatura

Los resultados dialogan con tres cuerpos de trabajo. Con la literatura de detección, confirman la advertencia de Sommer y Paxson (2010): las métricas agregadas no bastan. Un modelo con ROC-AUC de 0,958 puede tener un ECE de 0,042 y, aun así, producir un 7,6 % de autocierres erróneos. La evaluación operacional es la que revela ese riesgo. Con la literatura de LLM en SOC, los resultados matizan el pesimismo de Rieger et al. (2026). Ellos encontraron alta exhaustividad y baja precisión de priorización con modelos comerciales y 178 alertas; este estudio encuentra una precisión de escalamiento de 94,1 % con un modelo local, enriquecimiento y calibración. La diferencia no demuestra superioridad: el banco de pruebas es distinto, las etiquetas son operacionales y el escenario es simulado. Pero sugiere que el contexto y la calibración son variables moderadoras que merecen estudiarse sistemáticamente.

Con la literatura de colaboración humano-IA, el diseño es consistente con Singh et al. (2025) y Nath et al. (2026): el sistema automatiza la clasificación rutinaria y deja la decisión de alto riesgo al analista. La política de escalamiento y el campo `needs_human_review` materializan esa división. La contribución no es reemplazar la experticia, sino reducir la carga cognitiva asociada a la revisión de alertas repetitivas. Con la literatura de eficiencia, el enfoque se diferencia de Zhao et al. (2025): no se ajusta un experto LoRA ni se usa una arquitectura nube-borde, sino un modelo generalista local con herramientas. Esa elección sacrifica latencia (3,84 s vs. fracciones de segundo) y algo de precisión, pero reduce la complejidad de ingeniería y facilita la adopción en PYMES.

La comparación con BETO es particularmente informativa. BETO es un modelo supervisado ajustado, con 110 millones de parámetros y un costo de inferencia bajo; alcanzó 0,847 de macro-F1. SOC-Lite lo supera en 0,044, pero con una latencia 13,7 veces mayor y un costo de infraestructura superior. Para una organización con millones de alertas diarias, BETO podría ser preferible; para una PYME con cientos o miles de alertas diarias, el agente ofrece mejor calidad por alerta y una justificación textual que BETO no proporciona. La elección depende del volumen y de la necesidad de explicabilidad.

### 5.3. Implicaciones

**Teóricas.** El estudio sugiere que el triaje no es solo clasificación de texto ni solo detección de anomalías, sino una tarea de decisión basada en evidencia. El agente funciona como un integrador de fuentes heterogéneas: texto de la alerta, metadatos, reputación externa, geolocalización y memoria organizacional. Esa perspectiva conecta la literatura de LLM con la de sistemas de decisión y permite formular hipótesis sobre qué fuentes aportan valor en qué contextos. La jerarquía observada —inteligencia local > VirusTotal > AbuseIPDB > GeoIP— es una hipótesis que debería probarse en otros dominios.

**Metodológicas.** La evaluación demuestra la utilidad de combinar ablación, calibración y métricas operacionales. Reportar solo macro-F1 habría ocultado que la salida estructurada es el componente más importante y que la calibración afecta la política de decisión más que la discriminación. También muestra la necesidad de particiones por grupos: sin ellas, el rendimiento se habría inflado por fuga de plantillas. Los estudios futuros deberían adoptar protocolos similares para que los resultados sean comparables.

**Prácticas.** Para una PYME, el mensaje es que un SOC asistido por LLM es viable con infraestructura modesta, software de código abierto y un modelo local. La inversión principal no es la API del modelo, sino la integración, el enriquecimiento, la calibración y el monitoreo. El sistema reduce el esfuerzo rutinario, pero exige definir playbooks, umbrales y criterios de escalamiento. También exige aceptar que el modelo puede fallar y diseñar la degradación controlada.

**Organizacionales.** La adopción requiere gobernanza: registrar decisiones, auditar autocierres, revisar periódicamente la calibración y mantener un canal de retroalimentación con los analistas. Los marcos NIST CSF 2.0 e ISO/IEC 27001:2022 ofrecen el lenguaje para integrar esas prácticas en la gestión de seguridad. Sin gobernanza, el sistema puede convertirse en una caja negra que automatiza errores a escala.

### 5.4. Validez

**Validez interna.** El diseño controla la composición del banco de pruebas, la partición por grupos, la selección de hiperparámetros y la calibración. Sin embargo, las alertas son sintéticas y las plantillas pueden introducir artefactos que el agente aprende. La revisión manual simulada de 2.400 alertas reduce el riesgo de etiquetas inconsistentes, pero no lo elimina. La matriz de confusión simétrica es un indicio de que el escenario está más ordenado que la realidad; en producción, los errores suelen ser asimétricos. Los resultados deben leerse como una cota superior optimista del rendimiento esperado.

**Validez externa.** Los conjuntos de datos tienen varios años (CICIDS2017, UNSW-NB15) y no representan la diversidad de una PYME contemporánea. El modelo es único (llama3.1 8B) y el idioma de las alertas es inglés. Los resultados podrían cambiar con otros modelos, otros idiomas o arquitecturas de red distintas. La simulación de las APIs de enriquecimiento no captura la variabilidad, los límites de cuota ni los cambios de política de los proveedores. La generalización a un despliegue real requiere validación prospectiva.

**Validez de constructo.** La etiqueta operacional (VP/FP/SUS) es un constructo, no una verdad objetiva. Dos analistas pueden discrepar sobre si una alerta es sospechosa o falsa positiva. El κ de 0,86 indica una concordancia sustancial, pero también un margen de subjetividad. La severidad es aún más dependiente del contexto organizacional: un activo crítico para una empresa puede no serlo para otra. El estudio usa una definición explícita, pero no universal.

**Validez de conclusión estadística.** Los intervalos *bootstrap*, las pruebas de McNemar y la corrección de Bonferroni reducen el riesgo de falsos positivos. Sin embargo, las comparaciones múltiples y el tamaño del conjunto de prueba imponen límites. Las diferencias de 0,007 a 0,012 en la ablación son pequeñas y sus intervalos se solapan parcialmente; deben interpretarse como señales, no como pruebas definitivas. Los tamaños de efecto y la consistencia entre métricas son más informativos que cualquier *p* aislado.

### 5.5. Limitaciones

El estudio tiene seis limitaciones principales:

1. **Datos simulados.** Los valores numéricos provienen de un escenario calibrado, no de un despliegue productivo. No deben citarse como evidencia de rendimiento real.
2. **Edad y origen de los datos.** CICIDS2017 y UNSW-NB15 no reflejan el tráfico actual ni las particularidades de una PYME. Las plantillas de Wazuh/OPNsense mitigan parcialmente ese sesgo, pero no lo eliminan.
3. **Un solo modelo.** La evaluación se limita a llama3.1 8B; no se comparan GPT-4, Claude u otros modelos comerciales por restricciones de privacidad y costo. La ablación con Mistral 7B y Llama 3.1 70B es una aproximación, no una comparación exhaustiva.
4. **Enriquecimiento simulado.** Las APIs se reemplazaron por un *mock* determinista. La latencia y la calidad reales pueden diferir.
5. **Ausencia de evaluación adversarial.** No se probó inyección de *prompt*, envenenamiento de inteligencia ni manipulación de metadatos. Es una amenaza relevante en sistemas que procesan texto controlado por un adversario.
6. **Costo incompleto.** El costo reportado incluye tiempo de analista e infraestructura estimada, pero no ingeniería, mantenimiento, licencias ni capacitación. Un cálculo de costo total de propiedad sería más alto.

A esas limitaciones se añaden los riesgos documentados de los modelos fundacionales: opacidad, sesgos heredados de los datos de entrenamiento, uso dual y dependencia de prácticas de proveedores que no se auditan en este estudio (Bender et al., 2021; Bommasani et al., 2021). El diseño local reduce la exposición de datos, pero no elimina esos riesgos.

### 5.6. Trabajo futuro

Las limitaciones abren líneas concretas. Primero, un despliegue prospectivo en una PYME, en modo sombra, comparando las decisiones del sistema con las de los analistas durante al menos seis meses. Segundo, una evaluación adversarial que mida la resistencia a inyección de *prompt*, a indicadores falsos y a envenenamiento de la inteligencia local. Tercero, un ajuste con LoRA o QLoRA sobre trazas auditadas, para reducir latencia y mejorar la adaptación al dominio (Hu et al., 2022; Dettmers et al., 2023). Cuarto, un esquema de aprendizaje activo que incorpore la retroalimentación de los analistas y recalibre el modelo con deriva. Quinto, una comparación multi-modelo y multi-idioma, con modelos locales de distintos tamaños y arquitecturas. Sexto, un análisis de costo total de propiedad que incluya ingeniería y mantenimiento.

También sería valioso estudiar la interacción entre explicabilidad y confianza. El sistema produce una justificación breve, pero no se evaluó si esa justificación ayuda al analista a detectar errores. Un estudio con analistas reales podría medir el efecto de la explicación en la precisión y en el tiempo de revisión, y complementar la justificación textual con métodos de atribución como SHAP (Lundberg & Lee, 2017). Esa es una pregunta de investigación distinta, pero conectada: la utilidad de un clasificador no depende solo de su exactitud, sino de cómo se integra en el juicio humano. Asimismo, un ajuste por instrucción con retroalimentación humana (Ouyang et al., 2022) y mecanismos de alineación (Bai et al., 2022) podrían mejorar la consistencia del agente sin sacrificar la residencia de datos.
