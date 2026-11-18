# Pruebas de carga y clasificador IA (demo)

Guion de 10 minutos: instalar JMeter, cargar 100.000 alertas ficticias, correr el plan
de JMeter y mostrar el clasificador de triaje.

## Requisitos

- Java 17+ (probado con 21)
- PostgreSQL 18 instalado (solo se usan sus binarios)
- Python 3.11+ con las dependencias de `backend/requirements.txt`
- JMeter 5.6.x en `C:\tools\apache-jmeter-5.6.3`

JMeter se descarga de <https://dlcdn.apache.org/jmeter/binaries/apache-jmeter-5.6.3.zip>
y se descomprime en `C:\tools`. El ejecutable es `bin\jmeter.bat`.

## Quickstart

### 1. Base de datos de demo (puerto 55432, sin tocar la BD del proyecto)

```powershell
$pg = "C:\Program Files\PostgreSQL\18\bin"
$data = "$env:TEMP\pgload"
& "$pg\initdb.exe" -D $data -U postgres --auth=trust -E UTF8
& "$pg\pg_ctl.exe" -D $data -o "-p 55432" -l "$env:TEMP\pgload.log" start
& "$pg\psql.exe" -h localhost -p 55432 -U postgres -c "CREATE ROLE soclite LOGIN PASSWORD 'soclite' CREATEDB;" -c "CREATE DATABASE soclite OWNER soclite;"
```

### 2. Esquema, usuarios y 100k alertas

```powershell
$env:DATABASE_URL = "postgresql+asyncpg://soclite:soclite@localhost:55432/soclite"
cd backend
python -m app.seed
cd ..
psql "postgresql://soclite:soclite@localhost:55432/soclite" -f db/load_data.sql
```

Carga esperada: 100.000 alertas, 52.000 triajes, 240.000 enriquecimientos,
300.000 eventos de auditoría y 5.000 incidentes.

### 3. API sin LLM (triaje heurístico, respuesta determinista)

```powershell
cd backend
$env:LLM_PROVIDER = "none"
python -m uvicorn app.main:app --port 8000
```

### 4. Entrenar el clasificador IA (una vez)

```powershell
cd backend
python -m ml.train     # imprime accuracy y macro-F1, escribe ml/model.joblib
```

Endpoint: `POST /api/v1/triage/predict` (requiere JWT con `triage.execute`).

### 5. Prueba de carga

```powershell
New-Item -ItemType Directory -Force loadtest\results | Out-Null
C:\tools\apache-jmeter-5.6.3\bin\jmeter.bat -n -t loadtest\soclite.jmx `
  -l loadtest\results\runA.jtl -e -o loadtest\results\htmlA
```

Abrir `loadtest/results/htmlA/index.html`. Luego crear índices y repetir:

```powershell
psql "postgresql://soclite:soclite@localhost:55432/soclite" -f db/indexes.sql
C:\tools\apache-jmeter-5.6.3\bin\jmeter.bat -n -t loadtest\soclite.jmx `
  -l loadtest\results\runB.jtl -e -o loadtest\results\htmlB
```

## Plan de prueba

| Grupo | Hilos | Duración | Peticiones |
|---|---:|---:|---|
| setUp login | 1 | 1 iteración | `POST /auth/login/json`, token a propiedad global |
| Lectura dashboard | 40 | 90 s | `/alerts` paginado y filtrado, `/alerts/{id}`, `/metrics/overview`, `/incidents` |
| Escritura + IA | 10 | 60 s | `POST /alerts/webhook` (título único), `POST /triage/predict` |

Think time 300–800 ms (lectura) y 500–1000 ms (escritura).

## Resultados medidos (laptop, uvicorn 1 worker)

| Corrida | Muestras | Throughput | p95 | Errores | `/metrics/overview` avg |
|---|---:|---:|---:|---:|---:|
| A: esquema base | 2.664 | 28,0/s | 5,8 s | 0 % | 2.524 ms |
| B: con índices | 2.278 | 23,5/s | 5,8 s | 0 % | 3.493 ms |

Índices añadidos: `alerts(status)`, `alerts(severity, created_at)`, `audit_log(created_at)`.

### Hallazgos (lo interesante para exponer)

1. **El cuello de botella es la concurrencia, no el tamaño de la tabla.** `/metrics/overview`
   ejecuta 8 agregaciones y un `count(*)` global; con 40 hilos compite por CPU y conexiones.
2. **Los índices empeoraron el throughput.** Cada `GET` de auditoría escribe una fila en
   `audit_log`; indexar `created_at` encarece esas escrituras y no acelera las lecturas
   (el `GET /audit` está excluido de la bitácora). Resultado medido: −16 % de throughput.
   Conclusión honesta: no todo índice mejora; hay que medir.
3. **El pool por defecto (5+10) tumba la prueba a 40 hilos** con `QueuePool limit ... reached`.
   Se subió a 20+20 en `app/config.py` (`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`).
4. **`POST /triage/predict` responde en cientos de ms** con inferencia local, frente a
   segundos/minutos del LLM. El modelo es TF-IDF + regresión logística: accuracy 0,945 y
   macro-F1 0,926 sobre el conjunto sintético de prueba.

## Guion de 10 minutos

1. (1 min) `jmeter -v` y árbol del plan en la GUI: 3 grupos, token en setUp.
2. (2 min) Mostrar los 100k registros en psql y el dashboard con datos.
3. (3 min) Corrida JMeter A: throughput, p95, 0 % errores.
4. (2 min) Crear índices y corrida B: comparar cifras y explicar el hallazgo del punto 2.
5. (2 min) `ml/metrics.json` + tres predicciones en vivo con `curl`/Swagger.

## Limpieza

```powershell
& "C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe" -D "$env:TEMP\pgload" stop
```

`loadtest/results/` y `backend/ml/model.joblib` están en `.gitignore`.
