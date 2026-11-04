### 3.6. Diseño del agente, salida estructurada y calibración

El *prompt* del sistema tiene cuatro bloques. El primero define el rol: “analista de nivel 1 que clasifica alertas y decide si requieren escalamiento”. El segundo define la taxonomía operacional y las reglas de decisión, con ejemplos de VP, FP y SUS. El tercero describe las herramientas disponibles y las restricciones de uso. El cuarto impone el esquema JSON de salida y la instrucción de abstenerse cuando la evidencia sea insuficiente. Se incluyen tres ejemplos resueltos, seleccionados del conjunto de entrenamiento y nunca del de prueba, para ilustrar el formato y el nivel de justificación esperado. No se incluyen ejemplos de las mismas familias de plantilla que aparecen en prueba.

La salida estructurada cumple dos funciones. Primero, permite validar el resultado y activar el *fallback* si el modelo no cumple el esquema. Segundo, obliga al agente a explicitar la evidencia y la confianza, lo que facilita la auditoría. Sin salida estructurada, el sistema tendría que parsear texto libre, con errores frecuentes y sin garantías de consistencia. La ablación de la Sección 4.6 cuantifica ese efecto.

La calibración se realiza por *temperature scaling* sobre el conjunto de validación. Se ajusta un único parámetro de temperatura $T$ que minimiza la entropía cruzada de las probabilidades predichas, sin alterar el orden de las predicciones. El valor estimado fue $T = 1{,}37$. La calibración no cambia la clase predicha ni la macro-F1 del clasificador; cambia la interpretación de la confianza y, por tanto, las decisiones de autocierre y escalamiento. Esa distinción entre discriminación y calibración es central para interpretar los resultados: un modelo puede ordenar bien las alertas y, aun así, producir probabilidades mal calibradas (Guo et al., 2017).

El *fallback* heurístico es determinista y no depende del LLM. Calcula un puntaje de riesgo con una suma ponderada de cinco señales: severidad de la regla (0–1), criticidad del activo (0–1), coincidencia con inteligencia local (0 o 1), reputación del indicador (0–1) y anomalía de horario o frecuencia (0–1). Los pesos se fijaron con conocimiento experto y no se optimizaron sobre prueba: 0,30, 0,25, 0,20, 0,15 y 0,10, respectivamente. El puntaje se mapea a VP, SUS o FP con dos umbrales (0,62 y 0,38) y a severidad con reglas explícitas. El *fallback* se activó en el 1,2 % de las alertas de prueba (30 de 2.496), principalmente por *timeout* del modelo o por violación del esquema de salida.

### 3.7. Líneas base y variantes de ablación

Se compararon seis líneas base y el sistema propuesto:

1. **Heurístico.** El mismo *fallback* descrito, aplicado a todas las alertas. Es la referencia de menor costo y mayor interpretabilidad.
2. **Regresión logística.** Vectorización TF-IDF de palabras y caracteres, unigramas y bigramas, con regularización L2. Se eligió por su interpretabilidad y bajo costo.
3. **SVM con kernel RBF.** Misma representación TF-IDF, con búsqueda de $C$ y $\gamma$ en validación.
4. **Bosque aleatorio.** 500 árboles, profundidad ilimitada, mínimo de dos muestras por hoja, con características tabulares y texto vectorizado.
5. **XGBoost.** 600 estimadores, tasa de aprendizaje 0,05, profundidad máxima 6, submuestreo 0,9 y submuestreo de columnas 0,8.
6. **BETO ajustado.** Modelo `dccuchile/bert-base-spanish-wwm-cased`, cuatro épocas, tasa de aprendizaje 2 × 10⁻⁵, tamaño de lote 16, longitud máxima 256 y AdamW.
7. **SOC-Lite.** Agente local con enriquecimiento, salida estructurada y calibración.

Las variantes de ablación eliminan un componente a la vez: sin VirusTotal, sin AbuseIPDB, sin GeoIP, sin inteligencia local, sin salida estructurada y sin calibración. En la variante “sin salida estructurada”, el agente produce texto libre y un parser posterior extrae la etiqueta; si falla, se activa el *fallback*. En la variante “sin calibración”, se usan las probabilidades brutas del modelo. Todas las variantes comparten el mismo conjunto de prueba y la misma política de decisión, salvo la condición ablacionada.

### 3.8. Configuración experimental e hiperparámetros

La Tabla 3 resume el entorno, los hiperparámetros y la política de decisión. Todos los experimentos se ejecutaron en un servidor con 16 vCPU, 32 GB de RAM y una GPU NVIDIA RTX 4090 de 24 GB. El agente se sirvió con Ollama 0.3.x y se ejecutó en la GPU; los baselines tabulares se ejecutaron en CPU y BETO en GPU. La búsqueda de hiperparámetros se realizó con Optuna (Akiba et al., 2019) y validación cruzada de cinco pliegues sobre el conjunto de entrenamiento. Se fijaron semillas en 42 para la partición, el muestreo y la inicialización de modelos. Los componentes estocásticos (agente y BETO) se ejecutaron cinco veces; se reporta la media y la desviación estándar, salvo en latencia, donde se reporta la mediana.

**Tabla 3.** *Entorno experimental, hiperparámetros y política de decisión.*

| Componente | Configuración | Valor |
|---|---|---|
| **Entorno** | Sistema operativo | Ubuntu 22.04 LTS |
| | CPU / RAM | 16 vCPU / 32 GB |
| | GPU | NVIDIA RTX 4090, 24 GB |
| | Python / PyTorch | 3.11 / 2.3 |
| | scikit-learn / XGBoost | 1.4 / 2.0 |
| | FastAPI / PostgreSQL | 0.111 / 16 |
| | Ollama / LangChain | 0.3.x / 0.2 |
| **Agente** | Modelo | llama3.1 8B, Q5_K_M |
| | Temperatura / top-p | 0,1 / 0,9 |
| | Contexto / salida máxima | 8.192 / 1.024 tokens |
| | Reintentos / timeout | 1 / 30 s |
| | Semilla | 42 |
| | Ejemplos en el *prompt* | 3, del conjunto de entrenamiento |
| **Calibración** | Método | *Temperature scaling* |
| | Temperatura ajustada | 1,37 |
| | Conjunto de ajuste | Validación (1.248) |
| **Política** | Umbral de autocierre | Confianza ≥ 0,75, FP, sin malicia |
| | Umbral de revisión | Confianza < 0,60 o SUS |
| | Escalamiento inmediato | VP alta o indicador malicioso local |
| **Baselines** | Regresión logística | L2, $C$ = 1,0, TF-IDF 1–2 gramos |
| | SVM-RBF | $C$ = 10, $\gamma$ = *scale* |
| | Bosque aleatorio | 500 árboles, hoja mínima = 2 |
| | XGBoost | 600 árboles, $\eta$ = 0,05, profundidad 6 |
| | BETO | 4 épocas, $2\times10^{-5}$, lote 16, máx. 256 |
| **Evaluación** | Partición | 70/10/20 por grupos |
| | *Bootstrap* | 2.000 réplicas estratificadas |
| | Pruebas | McNemar, DeLong, Bonferroni |

*Nota.* La búsqueda de hiperparámetros se realizó con validación cruzada de 5 pliegues sobre el conjunto de entrenamiento y se confirmó en validación; el conjunto de prueba no se utilizó para seleccionar modelos ni umbrales. La temperatura de calibración se ajustó una sola vez sobre validación. El *fallback* heurístico se comparte entre el sistema propuesto y la línea base heurística para aislar el efecto del agente. Elaboración propia.

### 3.9. Métricas y análisis estadístico

La métrica principal es la macro-F1, porque equilibra las tres clases y no permite que la clase mayoritaria (FP) domine el resultado. Se reportan además exactitud, macro-precisión, macro-exhaustividad, ROC-AUC, PR-AUC, Brier score y error de calibración esperado (ECE). La ROC-AUC mide la capacidad de ordenar; la PR-AUC es más informativa con clases desbalanceadas; el Brier score combina calibración y resolución; el ECE cuantifica la diferencia media entre confianza y frecuencia observada en diez bins.

Para la severidad se reportan macro-F1, exactitud, kappa ponderada cuadrática (QWK) y F1 por clase. Para la operación se reportan precisión de escalamiento, proporción de FP en la cola escalada, cobertura de autocierre, error de autocierre, horas de analista por 1.000 alertas, costo por 1.000 alertas, MTTT y cumplimiento de SLA. Las horas y el costo se estiman con un costo de analista de USD 20 por hora; el costo de infraestructura se reporta por separado.

Los intervalos de confianza se calcularon con *bootstrap* estratificado de 2.000 réplicas (Efron, 1979). Las comparaciones de macro-F1 se realizaron con diferencias pareadas sobre las mismas réplicas, lo que preserva la correlación entre modelos. Las matrices de confusión se compararon con la prueba de McNemar (McNemar, 1947) y se aplicó una corrección de Bonferroni para seis comparaciones ($\alpha = 0{,}0083$). Las AUC se compararon con la prueba de DeLong et al. (1988). Se reportan tamaños de efecto absolutos y relativos; no se interpretan diferencias sin intervalo de confianza. El análisis sigue las recomendaciones de Dietterich (1998) para comparar clasificadores supervisados.

### 3.10. Ética, privacidad y reproducibilidad

El estudio no utiliza datos personales reales. Las alertas se construyeron con datos públicos y valores sintéticos; las direcciones IP y los identificadores de activos se anonimizaron o se generaron de forma artificial. No se enviaron datos a APIs externas de LLM. Las consultas de enriquecimiento, en el escenario simulado, se resolvieron con un *mock* local; en un despliegue real, se limitarían a los indicadores estrictamente necesarios y se aplicarían acuerdos de tratamiento de datos.

El artefacto implementa controles de seguridad alineados con ISO/IEC 27001:2022: autenticación de servicio, autorización basada en roles, registro de auditoría, separación de secretos y minimización de datos. El *dashboard* muestra solo la información necesaria para la decisión. Los resultados del agente incluyen una justificación breve y una lista de evidencia, lo que facilita la revisión humana y reduce el riesgo de automatización ciega.

La reproducibilidad se aborda en tres niveles. Primero, el banco de pruebas se genera con semillas fijas y plantillas documentadas. Segundo, el código de figuras y verificación de métricas se incluye en el repositorio. Tercero, el Apéndice B enumera los comandos, las versiones y las variables de entorno. El Apéndice C explica qué partes son simuladas y cuáles podrían reproducirse con APIs reales. La transparencia sobre la naturaleza simulada de los datos es una condición del estudio, no una nota accesoria.
