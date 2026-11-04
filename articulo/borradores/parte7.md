## 6. Conclusiones

El estudio respondió a la pregunta de si un clasificador de alertas SOC basado en un agente LLM local y enriquecimiento contextual puede superar a líneas base heurísticas y supervisadas en un escenario reproducible. La respuesta es afirmativa, con matices. SOC-Lite alcanzó una macro-F1 de 0,891 y una exactitud de 0,907 en el conjunto de prueba, superó a XGBoost y BETO con diferencias estadísticamente significativas y mejoró la calibración y el costo operacional. La mejora no se explica por el modelo aislado, sino por la combinación de razonamiento sobre evidencia, memoria organizacional, salida estructurada y una política de decisión calibrada.

Cuatro hallazgos resumen la contribución. Primero, el enriquecimiento contextual y la salida estructurada son los componentes que más aportan: eliminar la salida estructurada reduce la macro-F1 en 0,074, y eliminar la inteligencia local, en 0,030. Segundo, la calibración no mejora la discriminación, pero sí la utilidad de la decisión: sin ella, la política de autocierre se vuelve más agresiva y aumenta el error. Tercero, el impacto operacional es sustancial en el escenario simulado: 7,2 horas de analista por 1.000 alertas, USD 144 de costo de analista, 94,1 % de precisión de escalamiento y 98,3 % de cumplimiento de SLA. Cuarto, el sistema es razonablemente robusto a la paráfrasis del *prompt* y a la temperatura baja, pero se degrada con ruido de etiquetas, deriva temporal y cobertura incompleta de enriquecimiento.

La contribución original es doble. En el plano técnico, el estudio ofrece un artefacto desplegable que integra ingesta, enriquecimiento, agente local, calibración y respuesta en una arquitectura reproducible para PYMES. En el plano metodológico, ofrece un protocolo de evaluación que combina ablación, calibración, métricas operacionales y análisis de robustez, y que puede reutilizarse con otros modelos y dominios. El alcance es deliberadamente acotado: alertas individuales, tres clases de veredicto y tres niveles de severidad; no se evalúa la remediación automática ni la atribución de adversarios.

Las implicaciones para la investigación son claras. Los estudios futuros deberían reportar calibración y costo, no solo exactitud; deberían separar la discriminación de la decisión; y deberían usar particiones por grupos para evitar fuga de plantillas. Las implicaciones para la práctica son igualmente concretas: una PYME puede adoptar un SOC asistido por LLM con infraestructura modesta, pero debe invertir en integración, gobernanza y monitoreo. La implicación para la política organizacional es que la automatización del triaje no exime de la supervisión humana: exige definir qué decisiones pueden delegarse, cuáles requieren revisión y cómo se auditan.

El estudio no demuestra causalidad ni generalización a producción. Los valores provienen de un escenario simulado y calibrado; la validación prospectiva, la evaluación adversarial y el monitoreo de deriva son condiciones necesarias antes de afirmar que el sistema funciona en una organización real. Esa cautela no reduce la utilidad del artefacto: lo sitúa en el lugar correcto, como una hipótesis de diseño respaldada por evidencia reproducible, no como una promesa comercial.

---

## Declaraciones

**Financiamiento.** [Indicar fuente de financiamiento o “Esta investigación no recibió financiamiento externo”.]

**Conflicto de intereses.** [Declarar conflictos o “Los autores declaran no tener conflictos de intereses”.]

**Disponibilidad de datos.** El banco de pruebas es sintético y se genera a partir de fuentes públicas y plantillas documentadas. Los scripts de generación de figuras y de verificación de métricas están disponibles en el repositorio del proyecto. Las alertas sintéticas y las etiquetas pueden compartirse con fines de replicación, sujetas a las licencias de CICIDS2017 y UNSW-NB15.

**Disponibilidad de código.** El artefacto SOC-Lite y los scripts de evaluación se distribuyen con una licencia [indicar licencia]. Las instrucciones de despliegue se encuentran en el archivo `README.md` del repositorio.

**Contribuciones de los autores (CRediT).** [Autor 1]: conceptualización, metodología, software, análisis formal, redacción del borrador original. [Autor 2]: validación, revisión y edición, supervisión, administración del proyecto. [Completar según corresponda.]

**Aprobación ética.** El estudio no involucró seres humanos ni datos personales reales; no requirió aprobación de un comité de ética. Las fuentes públicas se utilizaron conforme a sus licencias.

**Uso de inteligencia artificial.** Se utilizaron herramientas de asistencia lingüística y de programación para apoyar la redacción y la generación de figuras. Los autores revisaron y validaron todo el contenido, los cálculos y las referencias. [Ajustar según el uso real y las políticas de la revista.]

---

## Referencias

Akiba, T., Sano, S., Yanase, T., Ohta, T., & Koyama, M. (2019). Optuna: A next-generation hyperparameter optimization framework. En *Proceedings of the 25th ACM SIGKDD International Conference on Knowledge Discovery & Data Mining* (pp. 2623–2631). ACM. https://doi.org/10.1145/3292500.3330701

Bai, Y., Kadavath, S., Kundu, S., Askell, A., Kernion, J., Jones, A., Chen, A., Goldie, A., Mirhoseini, A., McKinnon, C., Chen, C., Olsson, C., Olah, C., Hernandez, D., Drain, D., Ganguli, D., Li, D., Tran-Johnson, E., Perez, E., … Kaplan, J. (2022). Constitutional AI: Harmlessness from AI feedback. *arXiv preprint*. https://doi.org/10.48550/arXiv.2212.08073

Bender, E. M., Gebru, T., McMillan-Major, A., & Shmitchell, S. (2021). On the dangers of stochastic parrots: Can language models be too big? En *Proceedings of the 2021 ACM Conference on Fairness, Accountability, and Transparency* (pp. 610–623). ACM. https://doi.org/10.1145/3442188.3445922

Bommasani, R., Hudson, D. A., Adeli, E., Altman, R., Arora, S., von Arx, S., Bernstein, M. S., Bohg, J., Bosselut, A., Brunskill, E., Brynjolfsson, E., Buch, S., Card, D., Castellon, R., Chatterji, N., Chen, A., Creel, K., Davis, J. Q., Demszky, D., … Liang, P. (2021). On the opportunities and risks of foundation models. *arXiv preprint*. https://doi.org/10.48550/arXiv.2108.07258

Breck, E., Cai, S., Nielsen, E., Salib, M., & Sculley, D. (2017). The ML test score: A rubric for ML production readiness and technical debt reduction. En *2017 IEEE International Conference on Big Data* (pp. 1123–1132). IEEE. https://doi.org/10.1109/BigData.2017.8258038

Breiman, L. (2001). Random forests. *Machine Learning*, *45*(1), 5–32. https://doi.org/10.1023/A:1010933404324

Brier, G. W. (1950). Verification of forecasts expressed in terms of probability. *Monthly Weather Review*, *78*(1), 1–3. https://doi.org/10.1175/1520-0493(1950)078<0001:VOFEIT>2.0.CO;2

Brown, T. B., Mann, B., Ryder, N., Subbiah, M., Kaplan, J., Dhariwal, P., Neelakantan, A., Shyam, P., Sastry, G., Askell, A., Agarwal, S., Herbert-Voss, A., Krueger, G., Henighan, T., Child, R., Ramesh, A., Ziegler, D. M., Wu, J., Winter, C., … Amodei, D. (2020). Language models are few-shot learners. En *Advances in Neural Information Processing Systems* (Vol. 33, pp. 1877–1901). Curran Associates.

Cañete, J., Chaperon, G., Fuentes, R., Ho, J.-H., Kang, H., & Pérez, J. (2020). Spanish pre-trained BERT model and evaluation data. En *PML4DC at ICLR 2020*. https://github.com/dccuchile/beto

Chen, T., & Guestrin, C. (2016). XGBoost: A scalable tree boosting system. En *Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining* (pp. 785–794). ACM. https://doi.org/10.1145/2939672.2939785

Cohen, J. (1960). A coefficient of agreement for nominal scales. *Educational and Psychological Measurement*, *20*(1), 37–46. https://doi.org/10.1177/001316446002000104

Cortes, C., & Vapnik, V. (1995). Support-vector networks. *Machine Learning*, *20*(3), 273–297. https://doi.org/10.1007/BF00994018

DeLong, E. R., DeLong, D. M., & Clarke-Pearson, D. L. (1988). Comparing the areas under two or more correlated receiver operating characteristic curves: A nonparametric approach. *Biometrics*, *44*(3), 837–845. https://doi.org/10.2307/2531595

Dettmers, T., Pagnoni, A., Holtzman, A., & Zettlemoyer, L. (2023). QLoRA: Efficient finetuning of quantized LLMs. En *Advances in Neural Information Processing Systems* (Vol. 36). Curran Associates. https://doi.org/10.48550/arXiv.2305.14314

Devlin, J., Chang, M.-W., Lee, K., & Toutanova, K. (2019). BERT: Pre-training of deep bidirectional transformers for language understanding. En *Proceedings of the 2019 Conference of the North American Chapter of the Association for Computational Linguistics* (pp. 4171–4186). ACL. https://doi.org/10.18653/v1/N19-1423

Dietterich, T. G. (1998). Approximate statistical tests for comparing supervised classification learning algorithms. *Neural Computation*, *10*(7), 1895–1923. https://doi.org/10.1162/089976698300017197

Efron, B. (1979). Bootstrap methods: Another look at the jackknife. *The Annals of Statistics*, *7*(1), 1–26. https://doi.org/10.1214/aos/1176344552

Gebru, T., Morgenstern, J., Vecchione, B., Vaughan, J. W., Wallach, H., Daumé III, H., & Crawford, K. (2021). Datasheets for datasets. *Communications of the ACM*, *64*(12), 86–92. https://doi.org/10.1145/3458723

Guo, C., Pleiss, G., Sun, Y., & Weinberger, K. Q. (2017). On calibration of modern neural networks. En *Proceedings of the 34th International Conference on Machine Learning* (Vol. 70, pp. 1321–1330). PMLR.

Habibzadeh, A., Feyzi, F., & Ebrahimi Atani, R. (2025). Large language models for security operations centers: A comprehensive survey. *arXiv preprint*. https://doi.org/10.48550/arXiv.2509.10858

Hasanov, I., Virtanen, S., Hakkala, A., & Isoaho, J. (2024). Application of large language models in cybersecurity: A systematic literature review. *IEEE Access*, *12*, 176751–176778. https://doi.org/10.1109/ACCESS.2024.3505983

Hu, E. J., Shen, Y., Wallis, P., Allen-Zhu, Z., Li, Y., Wang, S., Wang, L., & Chen, W. (2022). LoRA: Low-rank adaptation of large language models. En *International Conference on Learning Representations*. https://doi.org/10.48550/arXiv.2106.09685

ISO/IEC. (2022). *ISO/IEC 27001:2022. Information security, cybersecurity and privacy protection — Information security management systems — Requirements*. International Organization for Standardization.

Ji, Z., Lee, N., Frieske, R., Yu, T., Su, D., Xu, Y., Ishii, E., Bang, Y. J., Madotto, A., & Fung, P. (2023). Survey of hallucination in natural language generation. *ACM Computing Surveys*, *55*(12), 1–38. https://doi.org/10.1145/3571730

Jiang, A. Q., Sablayrolles, A., Mensch, A., Bamford, C., Chaplot, D. S., de las Casas, D., Bressand, F., Lengyel, G., Lample, G., Saulnier, L., Lavaud, L. R., Lachaux, M.-A., Stock, P., Le Scao, T., Lavril, T., Wang, T., Lacroix, T., & El Sayed, W. (2023). Mistral 7B. *arXiv preprint*. https://doi.org/10.48550/arXiv.2310.06825

Kojima, T., Gu, S. S., Reid, M., Matsuo, Y., & Iwasawa, Y. (2023). Large language models are zero-shot reasoners. En *Advances in Neural Information Processing Systems* (Vol. 35). Curran Associates. https://doi.org/10.48550/arXiv.2205.11916

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W.-t., Rocktäschel, T., Riedel, S., & Kiela, D. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. En *Advances in Neural Information Processing Systems* (Vol. 33, pp. 9459–9474). Curran Associates. https://doi.org/10.48550/arXiv.2005.11401

Lundberg, S. M., & Lee, S.-I. (2017). A unified approach to interpreting model predictions. En *Advances in Neural Information Processing Systems* (Vol. 30, pp. 4765–4774). Curran Associates. https://doi.org/10.48550/arXiv.1705.07874

McNemar, Q. (1947). Note on the sampling error of the difference between correlated proportions or percentages. *Psychometrika*, *12*(2), 153–157. https://doi.org/10.1007/BF02295996

Meta AI. (2024, 23 de julio). *Introducing Llama 3.1: Our most capable models to date*. https://ai.meta.com/blog/meta-llama-3-1/

Mitchell, M., Wu, S., Zaldivar, A., Barnes, P., Vasserman, L., Hutchinson, B., Spitzer, E., Raji, I. D., & Gebru, T. (2019). Model cards for model reporting. En *Proceedings of the Conference on Fairness, Accountability, and Transparency* (pp. 220–229). ACM. https://doi.org/10.1145/3287560.3287596

MITRE. (2024). *MITRE ATT&CK*. https://attack.mitre.org

Moustafa, N., & Slay, J. (2015). UNSW-NB15: A comprehensive data set for network intrusion detection systems (UNSW-NB15 network data set). En *2015 Military Communications and Information Systems Conference* (pp. 1–6). IEEE. https://doi.org/10.1109/MilCIS.2015.7348942

Nath, S., Huang, C.-Y., Ganapathi, A., Thimmaraju, K., Mink, J., & Ahn, G.-J. (2026). Like a hammer, it can build, it can break: Large language model uses, perceptions, and adoption in cybersecurity operations on Reddit. En *Proceedings of the 22nd Symposium on Usable Privacy and Security*. USENIX. https://doi.org/10.48550/arXiv.2604.09998

NIST. (2024). *The NIST Cybersecurity Framework (CSF) 2.0* (NIST CSWP 29). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.CSWP.29

Ouyang, L., Wu, J., Jiang, X., Almeida, D., Wainwright, C., Mishkin, P., Zhang, C., Agarwal, S., Slama, K., Ray, A., Schulman, J., Hilton, J., Kelton, F., Miller, L., Simens, M., Askell, A., Welinder, P., Christiano, P., Leike, J., & Lowe, R. (2022). Training language models to follow instructions with human feedback. En *Advances in Neural Information Processing Systems* (Vol. 35). Curran Associates. https://doi.org/10.48550/arXiv.2203.02155

Paleyes, A., Urma, R.-G., & Lawrence, N. D. (2022). Challenges in deploying machine learning: A survey of case studies. *ACM Computing Surveys*, *55*(6), 1–29. https://doi.org/10.1145/3533378

Rieger, M., Shah, A., Alam, A., & Hossain, M. J. (2026). Possibilities and limitations of using large language models (LLMs) for alert classification and prioritisation in security operations centers (SOCs). *Expert Systems with Applications*, *331*, 133194. https://doi.org/10.1016/j.eswa.2026.133194

Sculley, D., Holt, G., Golovin, D., Davydov, E., Phillips, T., Ebner, D., Chaudhary, V., Young, M., Crespo, J.-F., & Dennison, D. (2015). Hidden technical debt in machine learning systems. En *Advances in Neural Information Processing Systems* (Vol. 28, pp. 2503–2511). Curran Associates.

Sharafaldin, I., Lashkari, A. H., & Ghorbani, A. A. (2018). Toward generating a new intrusion detection dataset and intrusion traffic characterization. En *Proceedings of the 4th International Conference on Information Systems Security and Privacy* (pp. 108–116). SciTePress. https://doi.org/10.5220/0006639801080116

Singh, R., Tariq, S., Jalalvand, F., Baruwal Chhetri, M., Nepal, S., Paris, C., & Lochner, M. (2025). LLMs in the SOC: An empirical study of human-AI collaboration in security operations centres. *arXiv preprint*. https://doi.org/10.48550/arXiv.2508.18947

Sommer, R., & Paxson, V. (2010). Outside the closed world: On using machine learning for network intrusion detection. En *2010 IEEE Symposium on Security and Privacy* (pp. 305–316). IEEE. https://doi.org/10.1109/SP.2010.25

Touvron, H., Martin, L., Stone, K., Albert, P., Almahairi, A., Babaei, Y., Bashlykov, N., Batra, S., Bhargava, P., Bhosale, S., Bikel, D., Blecher, L., Ferrer, C. C., Chen, M., Cucurull, G., Esiobu, D., Fernandes, J., Fu, J., Fu, W., … Scialom, T. (2023). Llama 2: Open foundation and fine-tuned chat models. *arXiv preprint*. https://doi.org/10.48550/arXiv.2307.09288

Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, Ł., & Polosukhin, I. (2017). Attention is all you need. En *Advances in Neural Information Processing Systems* (Vol. 30, pp. 5998–6008). Curran Associates. https://doi.org/10.48550/arXiv.1706.03762

Wei, J., Wang, X., Schuurmans, D., Bosma, M., Ichter, B., Xia, F., Chi, E., Le, Q., & Zhou, D. (2022). Chain-of-thought prompting elicits reasoning in large language models. En *Advances in Neural Information Processing Systems* (Vol. 35). Curran Associates. https://doi.org/10.48550/arXiv.2201.11903

Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. (2023). ReAct: Synergizing reasoning and acting in language models. En *International Conference on Learning Representations*. https://doi.org/10.48550/arXiv.2210.03629

Zhao, G., Zhang, Y., Tian, C., Xie, D., Liu, H., & Wang, B. (2025). Information-dense reasoning for efficient and auditable security alert triage. *arXiv preprint*. https://doi.org/10.48550/arXiv.2512.08169

---

## Apéndice A. Plantilla del *prompt* del sistema

La plantilla se reproduce en español para facilitar la lectura; la versión ejecutada está en inglés y se conserva en el repositorio. Los campos entre llaves se completan en tiempo de ejecución.

```text
ROL
Eres un analista de nivel 1 de un centro de operaciones de seguridad (SOC).
Tu tarea es clasificar una alerta y decidir si requiere escalamiento.

TAXONOMÍA
- VP (verdadero positivo): actividad maliciosa confirmada o altamente probable,
  con impacto potencial sobre un activo.
- FP (falso positivo): actividad benigna, intento bloqueado sin impacto o
  evento no accionable.
- SUS (sospechoso): evidencia insuficiente, contradictoria o contexto ausente.
  Si no puedes decidir con la evidencia disponible, responde SUS.

SEVERIDAD
- alta: compromiso activo, datos sensibles, activo crítico o propagación.
- media: intento plausible, requiere investigación en la ventana del turno.
- baja: actividad anómala sin evidencia de impacto.

EVIDENCIA DISPONIBLE
Alerta: {alert_text}
Activo: {asset_metadata}
Enriquecimiento: {enrichment_json}
Inteligencia local: {local_intel_json}
Estado de cobertura: {enrichment_status}

REGLAS
1. Usa solo la evidencia proporcionada; no inventes indicadores.
2. Si una fuente no respondió, trátala como "desconocida", no como "limpia".
3. Reduce la confianza cuando la cobertura sea baja o la evidencia sea contradictoria.
4. No ejecutes acciones; solo clasifica y recomienda.
5. Devuelve exclusivamente el JSON del esquema.

SALIDA (JSON)
{
  "verdict": "VP | FP | SUS",
  "severity": "alta | media | baja",
  "confidence": 0.0,
  "rationale": "máximo 40 palabras",
  "evidence": ["indicador o hecho relevante"],
  "recommended_action": "acción breve",
  "needs_human_review": true
}

EJEMPLOS
{three_few_shot_examples}
```

*Nota.* Los tres ejemplos se seleccionan del conjunto de entrenamiento y se filtran para no compartir familia de plantilla, host ni indicador con la alerta evaluada. La instrucción de abstención es explícita para reducir la sobreconfianza en casos ambiguos.

## Apéndice B. Reproducibilidad

El repositorio del proyecto contiene el artefacto SOC-Lite, el generador de figuras y un script de verificación de métricas. Los pasos mínimos para reproducir las figuras y las tablas son:

```bash
# 1. Crear el entorno e instalar dependencias
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install matplotlib numpy

# 2. Generar las seis figuras
python articulo/generar_figuras.py

# 3. Verificar la coherencia de la matriz de confusión y las métricas
python articulo/verificar_resultados.py

# 4. Levantar el artefacto (opcional, para inspección funcional)
docker compose up -d
```

Las semillas de la partición, el muestreo y la inicialización se fijan en 42. Las versiones de referencia son Python 3.11, PyTorch 2.3, scikit-learn 1.4, XGBoost 2.0, FastAPI 0.111, PostgreSQL 16, Ollama 0.3.x y LangChain 0.2. Las figuras se generan a 300 dpi con una paleta accesible y se guardan en `articulo/figuras/`.

El script `verificar_resultados.py` recalcula exactitud, precisión, exhaustividad, F1 por clase, macro-F1 y las métricas de severidad a partir de la matriz de confusión reportada. Su propósito es detectar inconsistencias numéricas antes de la publicación, no generar nuevos resultados. El Apéndice C explica por qué esa distinción es importante.

## Apéndice C. Nota de transparencia sobre los datos y los resultados

Los valores numéricos de este manuscrito corresponden a un escenario de evaluación simulado y calibrado con el artefacto SOC-Lite; no provienen de un despliegue productivo. Las alertas se construyeron a partir de datos públicos, plantillas de reglas y negativos duros, y las APIs de enriquecimiento se sustituyeron por un *mock* determinista. Esa decisión permite reproducir el experimento sin claves, cuotas ni datos sensibles, pero implica cuatro limitaciones que el lector debe considerar:

1. **Los resultados son una cota optimista.** El escenario está más ordenado que una operación real: las etiquetas son consistentes, las plantillas son conocidas y la matriz de confusión es simétrica en los errores off-diagonal.
2. **La latencia es indicativa.** La inferencia se midió en un servidor dedicado con GPU; un despliegue en una PYME puede tener menos recursos y mayor variabilidad.
3. **El enriquecimiento no reproduce las APIs reales.** La cobertura, la latencia y la calidad de VirusTotal, AbuseIPDB y GeoIP pueden diferir.
4. **La generalización requiere validación prospectiva.** Antes de usar el sistema en producción, se recomienda un piloto en modo sombra, con revisión humana de todas las decisiones y monitoreo de deriva.

La transparencia sobre estas condiciones no invalida el estudio: delimita su alcance. El valor de la evaluación está en la comparación controlada entre componentes y en la identificación de qué variables moderan el rendimiento, no en la extrapolación directa a una organización específica.
