## 4. Resultados

### 4.1. Descripción del conjunto de prueba

El conjunto de prueba contiene 2.496 alertas: 835 VP (33,5 %), 1.277 FP (51,2 %) y 384 SUS (15,4 %). La clase FP es mayoritaria, pero no de forma abrumadora; la clase SUS es la minoría y también la más difícil, porque su definición operacional exige evidencia insuficiente o contradictoria. La mediana de longitud del texto es 412 tokens y el 96,8 % de las alertas tiene al menos una fuente de enriquecimiento disponible. La cobertura es desigual: GeoIP es casi universal, mientras que la inteligencia local solo cubre el 22,6 %, lo que refleja la madurez típica de una PYME.

La distribución por fuente en prueba es proporcional a la del banco completo: 1.152 alertas de CICIDS2017, 576 de UNSW-NB15, 480 de Wazuh/OPNsense y 288 de negativos duros. Esa proporcionalidad permite comparar el rendimiento entre regímenes sin que una fuente domine el agregado. No se observaron diferencias estadísticamente significativas en la longitud del texto entre clases ($p = 0{,}18$, Kruskal-Wallis), lo que reduce el riesgo de que el agente use la longitud como atajo.

### 4.2. Rendimiento global frente a las líneas base

La Tabla 4 presenta los resultados principales. SOC-Lite obtuvo la mayor macro-F1 (0,891; IC 95 %: 0,881–0,901), seguido por BETO ajustado (0,847; 0,837–0,857) y XGBoost (0,829; 0,819–0,839). El heurístico quedó muy por debajo (0,641; 0,629–0,653), lo que confirma que las reglas simples no capturan la heterogeneidad del triaje. La diferencia absoluta frente a XGBoost fue de +0,062 (IC 95 %: 0,051–0,073) y frente a BETO, de +0,044 (0,033–0,055). Ambas diferencias son sustanciales y sus intervalos excluyen el cero.

![Figura 3. Curvas ROC y precisión-exhaustividad.](figuras/figura3_curvas.png)

**Figura 3.** *Curvas ROC y precisión-exhaustividad en el conjunto de prueba.* (a) Curvas ROC macro una-vs-resto para el heurístico, XGBoost, BETO ajustado y SOC-Lite. (b) Curvas precisión-exhaustividad. La línea punteada horizontal indica la prevalencia de la clase positiva (0,335) y corresponde al rendimiento de un clasificador aleatorio. Las curvas se construyeron a partir de las probabilidades calibradas del sistema propuesto y de las probabilidades nativas de los baselines. Elaboración propia.

La Figura 3 muestra que la ventaja de SOC-Lite no se limita a un umbral particular. La curva ROC se mantiene por encima de las demás en casi todo el rango de falsos positivos, y la curva PR conserva una precisión alta incluso con exhaustividad cercana a 0,8. El área bajo la curva ROC fue 0,958 y el PR-AUC, 0,931. BETO alcanzó 0,932 y 0,897; XGBoost, 0,921 y 0,882. La mejora en PR-AUC (+0,034 frente a BETO) es especialmente relevante porque la clase positiva es minoritaria y porque la cola de alertas es el recurso escaso.

**Tabla 4.** *Rendimiento comparativo en el conjunto de prueba (n = 2.496).*

| Modelo | Exactitud | Macro-precisión | Macro-exhaustividad | Macro-F1 [IC 95 %] | ROC-AUC | PR-AUC | Brier | ECE | Latencia (s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Heurístico | 0,704 | 0,652 | 0,631 | 0,641 [0,629–0,653] | 0,781 | 0,704 | 0,198 | 0,152 | 0,01 |
| Regresión logística | 0,768 | 0,749 | 0,736 | 0,742 [0,731–0,753] | 0,861 | 0,792 | 0,171 | 0,118 | 0,02 |
| SVM-RBF | 0,803 | 0,789 | 0,780 | 0,784 [0,774–0,794] | 0,889 | 0,824 | 0,149 | 0,103 | 0,04 |
| Bosque aleatorio | 0,818 | 0,806 | 0,797 | 0,801 [0,791–0,811] | 0,901 | 0,841 | 0,132 | 0,091 | 0,09 |
| XGBoost | 0,841 | 0,833 | 0,826 | 0,829 [0,819–0,839] | 0,921 | 0,882 | 0,111 | 0,055 | 0,12 |
| BETO ajustado | 0,856 | 0,850 | 0,845 | 0,847 [0,837–0,857] | 0,932 | 0,897 | 0,098 | 0,049 | 0,28 |
| **SOC-Lite** | **0,907** | **0,892** | **0,891** | **0,891 [0,881–0,901]** | **0,958** | **0,931** | **0,088** | **0,042** | **3,84** |

*Nota.* Los intervalos de confianza se calcularon con *bootstrap* estratificado de 2.000 réplicas. La latencia es la mediana por alerta, incluido el enriquecimiento y la inferencia, en el mismo servidor para todos los modelos. Las probabilidades de SOC-Lite están calibradas; las de los baselines son las nativas. ECE = error de calibración esperado en diez bins. El mejor valor de cada columna está en negrita. Elaboración propia.

El patrón es consistente con la hipótesis de que el contexto y la estructura explican la mejora. Los modelos supervisados aprenden de características agregadas y de texto vectorizado, pero no pueden consultar evidencia externa ni razonar sobre ella. El agente sí puede, y la diferencia se concentra en los casos ambiguos: alertas con indicadores de reputación mixta, activos críticos con reglas de baja severidad y negativos duros que se parecen a ataques. La Sección 4.6 descompone esa mejora por componente.

La latencia es el costo principal. SOC-Lite tardó 3,84 s por alerta, frente a 0,12 s de XGBoost y 0,28 s de BETO. En términos absolutos, 3,84 s es compatible con un flujo de triaje asíncrono en una PYME, pero no con un filtrado en línea de millones de eventos por segundo. Esa es una limitación de diseño, no un defecto del experimento: el sistema está pensado para alertas que ya superaron una etapa de detección y correlación, no para reemplazar el motor de detección.

La comparación estadística reforzó el patrón. La prueba de McNemar rechazó la igualdad de errores frente a XGBoost ($\chi^2 = 59{,}1$, $p < 0{,}001$), BETO ($\chi^2 = 38{,}8$, $p < 0{,}001$) y el heurístico ($\chi^2 = 357{,}0$, $p < 0{,}001$), con corrección de Bonferroni. La prueba de DeLong mostró diferencias significativas en ROC-AUC frente a los tres comparadores ($p < 0{,}001$). Los tamaños de efecto y los intervalos son más informativos que los valores *p*, pero ambos apuntan en la misma dirección.

### 4.3. Matriz de confusión, métricas por clase y severidad

La Figura 4 y la Tabla 5 desagregan el rendimiento. El sistema acertó 2.272 de 2.496 alertas (90,7 %). Los errores se distribuyen de forma asimétrica. La clase VP tuvo 760 aciertos, 50 confusiones con FP y 25 con SUS; la clase FP tuvo 1.190 aciertos, 50 confusiones con VP y 37 con SUS; la clase SUS tuvo 322 aciertos, 25 confusiones con VP y 37 con FP. La precisión y la exhaustividad son idénticas por clase porque la matriz es simétrica en los errores off-diagonal, una propiedad del escenario simulado que simplifica la interpretación pero no debe esperarse en producción.

![Figura 4. Matriz de confusión del agente.](figuras/figura4_matriz.png)

**Figura 4.** *Matriz de confusión del agente en el conjunto de prueba (n = 2.496).* Cada celda muestra el número absoluto y el porcentaje respecto de la clase real (fila). La escala de color representa el porcentaje de la fila. VP = verdadero positivo; FP = falso positivo; SUS = sospechoso. Elaboración propia.

La clase SUS es la más difícil: su F1 fue 0,839, frente a 0,910 de VP y 0,932 de FP. El sistema tiende a resolver la ambigüedad hacia una decisión binaria, sobre todo hacia FP. Esa tendencia es riesgosa en un SOC, porque un caso sospechoso convertido en falso positivo puede cerrarse sin revisión. La política de decisión mitiga el riesgo al exigir confianza ≥ 0,75 y ausencia de indicadores maliciosos para el autocierre; aun así, el 7,6 % de los autocierres fueron errores. La Tabla 5, panel C, muestra que la severidad es más difícil que el veredicto: la macro-F1 fue 0,853 y la exactitud, 0,861.

**Tabla 5.** *Matriz de confusión, métricas por clase y rendimiento de severidad.*

| **Panel A. Matriz de confusión (filas = clase real; columnas = clase predicha)** | | | | |
|---|---:|---:|---:|---:|
| Clase real | VP | FP | SUS | Total |
| VP | **760** | 50 | 25 | 835 |
| FP | 50 | **1.190** | 37 | 1.277 |
| SUS | 25 | 37 | **322** | 384 |
| Total | 835 | 1.277 | 384 | 2.496 |

| **Panel B. Métricas por clase de veredicto** | Precisión | Exhaustividad | F1 | Soporte |
|---|---:|---:|---:|---:|
| VP | 0,910 | 0,910 | 0,910 | 835 |
| FP | 0,932 | 0,932 | 0,932 | 1.277 |
| SUS | 0,839 | 0,839 | 0,839 | 384 |
| **Macro-promedio** | **0,892** | **0,891** | **0,891** | **2.496** |

| **Panel C. Métricas de severidad** | Precisión | Exhaustividad | F1 | Soporte |
|---|---:|---:|---:|---:|
| Alta | 0,872 | 0,864 | 0,868 | 612 |
| Media | 0,854 | 0,874 | 0,864 | 1.104 |
| Baja | 0,814 | 0,838 | 0,826 | 780 |
| **Macro-promedio** | **0,847** | **0,859** | **0,853** | **2.496** |

*Nota.* Exactitud global del veredicto = 0,907; exactitud de severidad = 0,861; kappa ponderada cuadrática de severidad = 0,782. La matriz del panel A es simétrica en los errores off-diagonal por construcción del escenario simulado; no se debe asumir esa propiedad en datos reales. Los soportes de severidad suman 2.496. Elaboración propia.

La severidad alta tuvo un F1 de 0,868 y la baja, de 0,826. El patrón sugiere que el sistema identifica bien los incidentes críticos, pero confunde con más frecuencia la severidad baja con media. Esa confusión es menos costosa que la inversa, porque una alerta baja escalada como media consume tiempo, mientras que una alerta alta degradada a media puede retrasar la respuesta. La política de escalamiento compensa parcialmente ese riesgo al enviar a revisión humana cualquier VP con activo crítico, independientemente de la severidad predicha.

### 4.4. Calibración y distribución de la confianza

La Figura 5 presenta el diagrama de fiabilidad y la distribución de confianza según acierto. SOC-Lite fue el modelo mejor calibrado: ECE de 0,042 y Brier de 0,088. BETO obtuvo ECE de 0,049 y Brier de 0,098; XGBoost, 0,055 y 0,111. La diferencia puede parecer pequeña, pero es operacionalmente relevante: con 2.496 alertas, un ECE de 0,042 implica que la confianza declarada se desvía, en promedio, cuatro puntos porcentuales de la frecuencia observada. Esa desviación es aceptable para umbrales de autocierre, aunque no elimina la necesidad de revisión humana.

![Figura 5. Calibración y distribución de la confianza.](figuras/figura5_calibracion.png)

**Figura 5.** *Calibración y distribución de la confianza.* (a) Diagrama de fiabilidad con diez bins para SOC-Lite, XGBoost y BETO; la diagonal punteada representa calibración perfecta. (b) Distribución de la confianza del agente para predicciones correctas (n = 2.272) e incorrectas (n = 224); la línea vertical punteada marca el umbral de autocierre de 0,75. Elaboración propia.

La distribución de la confianza muestra una separación clara entre aciertos y errores, pero con solapamiento en la zona media. Las predicciones correctas se concentran por encima de 0,75; las incorrectas, por debajo de 0,6. El umbral de autocierre de 0,75 captura una fracción importante de los aciertos y deja fuera a la mayoría de los errores, aunque no a todos. El 7,6 % de autocierres erróneos proviene, en su mayoría, de alertas SUS que el agente clasificó como FP con confianza alta. Ese es el fallo más costoso del sistema y la razón por la que la política exige ausencia de indicadores maliciosos y criticidad baja o media.

La calibración también explica por qué la macro-F1 del sistema end-to-end (0,891) es ligeramente inferior a la del agente sin *fallback* (0,894). El *fallback* afecta al 1,2 % de las alertas y su heurístico es menos preciso que el agente. La diferencia es pequeña, pero muestra que la degradación controlada tiene un costo medible. En un despliegue real, ese costo sería preferible a una caída total del servicio o a un resultado sin validación de esquema.
