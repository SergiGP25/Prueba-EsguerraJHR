# Motor contable

Módulo contable para empresas colombianas: plan de cuentas, comprobantes con partida doble,
reversión trazable, libro mayor e información exógena en XML.

**Stack:** FastAPI · PostgreSQL 16 · Next.js 16 (App Router, TypeScript) · Docker Compose.

---

## 1. Levantar el proyecto

### Con Docker (recomendado, un solo comando)

```bash
cp .env.example .env
docker compose up --build
```

Esto levanta la base de datos, aplica las migraciones automáticamente y arranca API y frontend:

| Servicio | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| Documentación interactiva | http://localhost:8000/docs |

Cargue los datos de demostración (empresa, plan de cuentas, terceros, períodos y UVT):

```bash
docker compose exec backend python -m scripts.seed
```

> **Puertos ocupados.** Si 3000, 8000 o 5432 ya están en uso, cámbielos en `.env`
> (`FRONTEND_PORT`, `BACKEND_PORT`, `POSTGRES_PORT`). El CORS del backend se ajusta solo
> a partir de `FRONTEND_PORT`.

> **Redes corporativas.** Si su red intercepta TLS y `npm ci` falla dentro de Docker con
> `SELF_SIGNED_CERT_IN_CHAIN`, construya con
> `NPM_CONFIG_STRICT_SSL=false docker compose up --build`. La verificación de certificados
> está activa por defecto.

### Sin Docker

```bash
# Base de datos
docker compose up -d db

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --reload

# Frontend (en otra terminal)
cd frontend
npm install
npm run dev
```

## 2. Migraciones

Se gestionan con Alembic desde `backend/`:

```bash
alembic upgrade head          # aplicar todo
alembic downgrade -1          # revertir la última
alembic revision -m "mensaje" # crear una nueva (se escribe a mano, sin autogenerate)
```

Dentro de Docker, `entrypoint.sh` ejecuta `alembic upgrade head` antes de arrancar la API,
así que un entorno limpio no requiere pasos manuales.

| Revisión | Contenido |
|---|---|
| `0001_inicial` | Empresas, cuentas, terceros, períodos, comprobantes y líneas. |
| `0002_reversion` | Estado `reversado` y enlace al comprobante original. |
| `0003_uvt` | Valor de UVT por año y bitácora de sincronizaciones. |
| `0004_exogena` | Histórico de generaciones y DV opcional del tercero. |

## 3. Pruebas

```bash
cd backend
pip install -r requirements-dev.txt
pytest                                   # 70 pruebas
pytest --cov=app --cov-report=term       # con cobertura (92%)
```

Las pruebas necesitan un PostgreSQL accesible. Por defecto usan
`postgresql+psycopg://contable:contable@localhost:5432/contable_test` (la base se crea sola);
sobrescriba con `TEST_DATABASE_URL` si hace falta.

También pueden ejecutarse sin instalar nada en local:

```bash
docker compose up -d db
docker build --target dev -t contable-backend-dev ./backend
docker run --rm --network prueba-esguerrajhr_default \
  -e TEST_DATABASE_URL="postgresql+psycopg://contable:contable@contable-db:5432/contable_test" \
  contable-backend-dev pytest
```

### Qué se probó y por qué

No se buscó cobertura exhaustiva sino proteger las reglas cuyo fallo sería silencioso y caro:

| Archivo | Riesgo que cubre |
|---|---|
| `test_contabilizar.py` | Partida doble, mínimo de líneas, débito/crédito excluyentes, cuentas activas, período abierto, numeración consecutiva, inmutabilidad del comprobante contabilizado y ausencia de estado parcial tras un fallo. |
| `test_reversion.py` | Que el espejo invierta correctamente, que el original quede marcado y conserve sus movimientos, que no se pueda reversar dos veces y que respete el cierre de período. |
| `test_libro_mayor.py` | Signo del saldo según la naturaleza de la cuenta, exclusión de borradores, saldo inicial y neteo de una reversión. |
| `test_exogena.py` | Agrupación por tercero y concepto, umbral en UVT con exclusión trazable, cuadre de totales de control y re-descarga idéntica byte a byte. |
| `test_nit.py` | Algoritmo del dígito de verificación contra NIT públicos verificables. |
| `test_uvt.py` | Reintentos ante fallos transitorios, idempotencia y registro de cada ejecución. |
| `test_money.py` | Que ningún monto pase por coma flotante. |

Se usa **PostgreSQL real, no SQLite**: el dominio depende de enums nativos, `NUMERIC(18,2)` y
`SELECT ... FOR UPDATE`, que en otro motor se comportan distinto. Probar contra SQLite daría
confianza falsa justo en lo que más importa.

## 4. Decisiones de diseño

### Precisión monetaria (Escenario 5)

`NUMERIC(18,2)` en PostgreSQL, `Decimal` en Python y **string en JSON**. Un `number` de JSON
es un `double` IEEE-754: `1190000.10` no tiene representación exacta. Enviar `"1190000.10"`
evita esa pérdida en la frontera del API. En el navegador los totales se calculan en
**centavos enteros** (`frontend/lib/money.ts`), exactos hasta 2^53, y solo se convierten a
número para formatear con `Intl.NumberFormat('es-CO')`.

### Plan de cuentas plano

Cada cuenta tiene código, nombre, naturaleza y estado activo/inactivo, sin jerarquía. Para el
alcance de la prueba una jerarquía PUC no aporta: ninguna regla la consulta. Añadir
`cuenta_padre_id` después no rompe los movimientos ya registrados, porque las líneas apuntan a
la cuenta hoja. La naturaleza sí se usa: determina el signo del saldo en el libro mayor.

### Período derivado de la fecha

El período `YYYY-MM` se obtiene o se crea a partir de la fecha del comprobante. Evita que el
usuario pueda asociar un comprobante de enero a un período de marzo, un error de captura
frecuente y difícil de detectar después.

### Contabilización atómica y concurrencia (Escenario 6)

`contabilizar()` corre en una sola transacción: toma un `SELECT ... FOR UPDATE` sobre la fila
del período, valida, asigna `numero = max(numero) + 1` y cambia el estado.

- **Qué garantiza:** dos peticiones simultáneas sobre la misma empresa y período se serializan
  en el lock, de modo que no pueden obtener el mismo número. Como respaldo, la restricción
  única `(empresa_id, periodo_id, numero)` lo impide también a nivel de base de datos.
- **Ante fallos parciales:** cualquier excepción revierte la transacción completa; nunca queda
  un comprobante numerado a medias ni un estado cambiado sin sus líneas.
- **Costo:** el lock serializa las contabilizaciones *de un mismo período*; distintos períodos o
  empresas no se bloquean entre sí. A la escala de esta aplicación es intrascendente. Si el
  volumen lo exigiera, la numeración pasaría a una secuencia por período.

### Reversión (Escenario 3)

Un comprobante contabilizado **nunca se edita ni se borra**. La reversión crea un comprobante
espejo con débitos y créditos intercambiados, lo contabiliza reutilizando `contabilizar()`
(hereda lock, numeración y validaciones) y marca el original como `reversado`.

Ambos permanecen en el libro mayor y su efecto neto es cero. Se prefirió esto a un borrado
lógico porque la trazabilidad contable exige poder responder *qué se registró, cuándo y cómo se
corrigió*, no solo cuál es el saldo actual. La restricción única sobre `reversa_comprobante_id`
hace imposible reversar dos veces incluso ante una condición de carrera.

La reversión se registra por defecto en la fecha del original; si ese período ya está cerrado,
se exige una fecha dentro de un período abierto.

### Libro mayor: saldo acumulado en tiempo real

El saldo se calcula recorriendo los movimientos del rango, partiendo de un saldo inicial que se
agrega en una sola consulta sobre los movimientos anteriores.

- **Consistencia:** siempre refleja exactamente los movimientos registrados; no existe un
  acumulado que pueda quedar desincronizado.
- **Concurrencia:** al no mantener un contador compartido, no hay contención ni riesgo de doble
  conteo entre consultas y escrituras simultáneas.
- **Rendimiento:** es lineal en el número de movimientos del rango, ya filtrado por cuenta y
  fechas. A partir de cientos de miles de movimientos por cuenta convendría materializar saldos
  mensuales y calcular solo el tramo restante; el cambio quedaría contenido en
  `services/reporting.py`.

La lógica de signo según naturaleza (débito: `saldo += D − C`; crédito: `saldo += C − D`) se
resolvió en Python y no con una función de ventana en SQL: la misma ramificación habría que
escribirla igual en SQL y allí resulta menos legible.

### Información exógena

- El **NIT del informante se valida** con el algoritmo DIAN antes de generar; si no cuadra, la
  operación se aborta con `NIT_DV_INVALIDO`.
- Los movimientos se **agrupan por tercero y concepto**. El concepto se deduce del primer dígito
  del código PUC (4 → ingresos `1007`, 5/6/7 → pagos `5001`, etc.) mediante un diccionario en
  `services/exogena.py`. Es una simplificación consciente: en producción sería una tabla
  configurable por empresa y año, porque los conceptos cambian con cada resolución.
- Las cuentas de retención (`2365`, `2367`, `2368`) alimentan `valorRetencion` y no inflan el
  `valorBruto`.
- El **umbral se expresa en UVT** y se convierte a pesos con el valor del año gravable. Los
  terceros por debajo se excluyen dejando traza tanto en el log como en la columna
  `exclusiones` de la generación, para poder explicar después por qué alguien no aparece.
- Los **totales de control** se calculan sobre los registros efectivamente incluidos.
- Cada generación guarda fecha, parámetros, totales, exclusiones y el propio XML, lo que hace
  trivial la **re-descarga** por identificador sin depender de un sistema de archivos.

### Integración externa: valor de la UVT

`POST /api/uvt/sincronizar?anio=` responde **202 inmediatamente** y delega el trabajo a
`BackgroundTasks`, que abre su propia sesión de base de datos. La petición HTTP nunca queda
bloqueada esperando a la fuente externa.

- **Fallos transitorios:** se reintenta hasta tres veces con espera creciente.
- **Sin duplicados:** el valor se guarda con `INSERT ... ON CONFLICT (anio) DO UPDATE`, así que
  repetir la sincronización actualiza en lugar de duplicar.
- **Trazabilidad:** cada ejecución escribe una fila en `uvt_sincronizaciones` (éxito o fallo,
  número de intentos, detalle del error), consultable en `GET /api/uvt/sincronizaciones`.

Se usa un **proveedor simulado** con los valores oficiales de la DIAN. Está detrás de un
`Protocol` (`ProveedorUvt`), de modo que sustituirlo por un cliente HTTP real no toca la lógica
de sincronización ni las pruebas. No se intentó raspar el sitio de la DIAN: el enunciado admite
un proveedor simulado y el código de integración —reintentos, idempotencia, trazabilidad— es
idéntico en ambos casos.

Se descartó Celery/Redis: añadiría dos servicios y un broker para una tarea que se ejecuta
esporádicamente y cuya pérdida no es crítica (se puede reintentar).

### Separación de responsabilidades

```
backend/app/
  models/      Persistencia: tablas y relaciones (SQLAlchemy 2.0).
  schemas.py   Contrato del API: validación de entrada y forma de salida (Pydantic).
  services/    Reglas de negocio. No conocen HTTP.
    accounting.py  Escritura: borradores, contabilización, reversión, cierre.
    reporting.py   Lectura: libro mayor y saldos.
    uvt.py         Integración externa.
    exogena.py     Generación del archivo.
  core/        Dominio puro y reutilizable: dinero, NIT, errores.
  api.py       Exposición HTTP: rutas delgadas que traducen y confían en los servicios.
```

Las rutas no contienen reglas contables: validan lo que es responsabilidad del transporte
(existencia de recursos, forma del payload), llaman al servicio y confirman la transacción. Los
servicios lanzan `DomainError(codigo, mensaje)`, que un único manejador traduce a
`{"code", "detail"}` con 422 o 409. Por eso el frontend puede mapear códigos a mensajes
accionables sin interpretar textos.

En el frontend, `lib/api.ts` es el único módulo que conoce la URL del backend, `lib/errors.ts`
el único que normaliza sus tres formas de error, y `lib/money.ts` el único que hace aritmética
monetaria.

### Frontend: Server Components y sin librería de datos

Las páginas son Server Components que resuelven catálogos (empresa, cuentas, terceros) en el
servidor y los pasan como props; solo son Client Components las piezas con interacción real
(formulario de comprobantes, filtros, generación de exógena).

El libro mayor toma sus filtros de los `searchParams`: la consulta queda en la URL, es
compartible y el estado de carga lo da el propio framework.

No se añadió TanStack Query ni SWR. Con tres vistas, sin caché compartida ni actualizaciones
optimistas, `router.refresh()` cubre la revalidación y la dependencia no se justifica.

## 5. Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Estado del servicio. |
| POST/GET | `/api/empresas` | Crear y listar empresas. |
| POST/GET | `/api/empresas/{id}/cuentas` | Plan de cuentas. |
| PATCH | `/api/cuentas/{id}` | Activar/inactivar o renombrar. |
| POST/GET | `/api/empresas/{id}/periodos` | Períodos contables. |
| POST | `/api/periodos/{id}/cerrar` | Cierre de período. |
| POST/GET | `/api/empresas/{id}/terceros` | Terceros. |
| POST/GET | `/api/empresas/{id}/comprobantes` | Crear borrador y listar (paginado). |
| GET/PUT | `/api/comprobantes/{id}` | Consultar y editar borrador. |
| POST | `/api/comprobantes/{id}/contabilizar` | Contabilización atómica. |
| POST | `/api/comprobantes/{id}/revertir` | Reversión trazable. |
| GET | `/api/empresas/{id}/libro-mayor` | Movimientos con saldo acumulado. |
| POST | `/api/exogena/generar` | Genera el XML y lo descarga. |
| GET | `/api/exogena/historial` | Generaciones previas. |
| GET | `/api/exogena/historial/{id}/archivo` | Re-descarga. |
| POST | `/api/uvt/sincronizar` | Encola la sincronización (202). |
| GET | `/api/uvt`, `/api/uvt/sincronizaciones` | Valores y bitácora. |

### Códigos de error de dominio

`PARTIDA_DOBLE`, `LINEAS_INSUFICIENTES`, `DEBITO_Y_CREDITO`, `VALOR_INVALIDO`,
`CUENTA_INACTIVA`, `CUENTA_NO_ENCONTRADA`, `TERCERO_NO_ENCONTRADO`, `PERIODO_CERRADO`,
`PERIODO_YA_CERRADO`, `COMPROBANTE_PROTEGIDO`, `COMPROBANTE_YA_REVERSADO`,
`REVERSION_ESTADO_INVALIDO`, `ESTADO_INVALIDO`, `UVT_NO_DISPONIBLE`, `NIT_DV_INVALIDO`,
`RANGO_INVALIDO`.

## 6. Reapertura de período

**No está implementada, por decisión.** Reabrir un período que ya se cerró (y probablemente se
reportó) es una operación sensible: cambia cifras que alguien ya usó. Exponerla como un endpoint
más, sin control de acceso ni rastro, sería el tipo de facilidad que se vuelve un problema.

Cómo la abordaría:

1. **Autorización explícita.** Solo un rol contable autorizado; no basta con estar autenticado.
2. **Motivo obligatorio y auditoría.** Una tabla `periodo_auditoria` con quién reabrió, cuándo,
   por qué y qué comprobantes se registraron durante la reapertura.
3. **Reapertura acotada.** El período vuelve a `abierto` y se marca `reabierto_en`; al cerrarlo
   de nuevo queda constancia de que hubo movimientos posteriores al primer cierre.
4. **Restricción de cascada.** No permitir reabrir un período si hay períodos posteriores
   cerrados, para no invalidar saldos ya arrastrados. La alternativa —y lo que suele hacerse en
   la práctica— es registrar el ajuste en el período abierto actual mediante una reversión, que
   sí está implementada.

## 7. Limitaciones conocidas

- **Sin autenticación ni multiusuario.** No hay JWT ni roles: cualquiera que alcance la API
  puede operar. Es lo primero que añadiría (ver sección 9).
- **Mapeo de conceptos de exógena simplificado.** Diccionario por prefijo PUC en código, no
  tabla configurable por año.
- **Retención imputada al registro de mayor valor bruto** del tercero cuando tiene varios
  conceptos. Con un catálogo real de conceptos, la retención se asociaría a su concepto propio.
- **Proveedor de UVT simulado**, con valores oficiales embebidos.
- **Sin pruebas automatizadas de frontend.** Se priorizaron las reglas contables del backend,
  donde un error es silencioso y costoso; en el frontend un error es visible de inmediato.
- **Paginación por `offset`** en el listado de comprobantes: suficiente aquí, se degrada con
  volúmenes grandes.
- **Cierre de período sin asientos de cierre.** Cerrar bloquea movimientos, pero no genera la
  cancelación de cuentas de resultado contra utilidades del ejercicio.
- **Una sola moneda** (COP), sin conversión ni ajuste por diferencia en cambio.

## 8. Pendientes

| Pendiente | Cómo lo abordaría |
|---|---|
| Pruebas de frontend | Vitest + Testing Library para `money.ts` y `errors.ts` (lógica pura), y una prueba de integración del formulario que verifique totales y manejo de errores. |
| Administración de plan de cuentas y terceros desde la UI | Ya existen los endpoints; falta un CRUD sencillo. Hoy se cargan con el seed. |
| Cierre de período desde la UI | El endpoint existe; falta la vista con la confirmación correspondiente. |
| Balance de prueba | Misma consulta del libro mayor agregada por cuenta; reutilizaría `reporting.py`. |
| Exportación del libro mayor a Excel | Un endpoint que reutilice `libro_mayor()` y serialice con `openpyxl`. |

## 9. ¿Qué cambiaría para producción?

1. **Autenticación y autorización.** JWT con roles (consulta / registro / cierre). Todas las
   operaciones que mutan estado contable deben quedar atribuidas a un usuario.
2. **Auditoría completa del ciclo de vida.** Hoy la trazabilidad vive en el propio modelo
   (estados, reversión enlazada, `created_at`/`updated_at`, bitácoras de UVT y exógena). En
   producción añadiría una tabla de eventos con actor, acción, momento y valores anteriores.
3. **Gestión de secretos.** Las credenciales viajan hoy por `.env`. Irían a un gestor de
   secretos, nunca al repositorio ni a la imagen.
4. **Cola real para tareas externas.** `BackgroundTasks` muere con el proceso. Con más
   integraciones, un worker con cola persistente y reintentos con backoff exponencial.
5. **Observabilidad.** Logs estructurados en JSON con identificador de correlación, métricas de
   latencia y error por endpoint, y trazas. Hoy hay logging estándar.
6. **Migraciones seguras y respaldos.** Ejecutar migraciones como paso previo del despliegue y
   no dentro del arranque de cada réplica, más respaldos verificados con restauración probada.
7. **Rendimiento a escala.** Paginación por cursor, índices sobre `(empresa_id, fecha)` en
   comprobantes y saldos mensuales materializados si el libro mayor lo pide.
8. **Almacenamiento de archivos.** Los XML de exógena a un almacenamiento de objetos con URLs
   firmadas, en lugar de una columna `TEXT`.
9. **Endurecimiento del contenedor.** Imágenes con versión fijada por digest, escaneo de
   vulnerabilidades en el pipeline y límites de recursos.

## 10. Integración continua

`.github/workflows/ci.yml` ejecuta en cada push y pull request:

- **`backend-lint`** — `ruff check` sobre el backend.
- **`backend-tests`** — levanta un PostgreSQL 16 real como service container, aplica las
  migraciones desde cero (lo que valida que sean correctas, no solo los modelos) y corre
  `pytest --cov`, publicando el reporte de cobertura como artefacto.
- **`frontend`** — `npm ci`, `npm run lint` y `npm run build`.

`.github/workflows/codeql.yml` ejecuta **CodeQL** sobre Python y TypeScript, más un barrido
semanal programado.

Sobre el análisis de código: CodeQL es análisis **estático** (busca patrones de vulnerabilidad
sin ejecutar el código), mientras que la evidencia **dinámica** la aporta el job de pruebas, que
ejecuta el sistema completo contra una base de datos real y mide qué quedó cubierto. Se
prefirieron a SonarCloud porque no requieren cuentas ni tokens externos: el evaluador puede
hacer fork del repositorio y el pipeline funciona sin configuración.

## 11. Escenarios del enunciado

Todos están cubiertos por pruebas automatizadas y se pueden reproducir desde la interfaz:

| Escenario | Resultado | Dónde se verifica |
|---|---|---|
| 1. Compra válida (1.000.000 + 190.000 = 1.190.000) | Contabiliza y asigna número | `test_contabilizar.py` |
| 2. Desbalanceado (500.000 vs 450.000) | Rechazo 422 `PARTIDA_DOBLE` con los totales en el mensaje | `test_contabilizar.py` |
| 3. Reversión | Comprobante espejo enlazado; original `reversado`; ambos visibles en el mayor con neto cero | `test_reversion.py`, `test_libro_mayor.py` |
| 4. Período 2025-01 cerrado | Rechazo 409 `PERIODO_CERRADO` al crear y al contabilizar | `test_contabilizar.py` |
| 5. Precisión monetaria | `Decimal`/`NUMERIC(18,2)` y strings en JSON; centavos enteros en el navegador | `test_money.py` |
| 6. Operaciones concurrentes | Lock del período más restricción única sobre el número | `test_contabilizar.py` (numeración consecutiva) |

## 12. Extensiones incluidas

Además del núcleo pedido:

- **Docker Compose completo:** todo el sistema con `docker compose up --build`, migraciones
  incluidas. Es lo que más peso tiene para quien evalúa: elimina la fricción de montar el
  entorno y garantiza que lo que funciona aquí funciona allá.
- **Pipeline de CI con CodeQL y cobertura**, por la misma razón: hace verificable lo que el
  README afirma.
- **Cabecera `X-Generacion-Id`** en la descarga de exógena, para que el cliente pueda referenciar
  la generación sin una segunda petición.
