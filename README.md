# Caso Red Eléctrica · MCOI (UPV)

Modelo de programación lineal entera mixta (MILP) que calcula la programación horaria de coste mínimo de un
día tipo en un sistema eléctrico con seis centrales (dos hidráulicas con bombeo), cinco centros de
transformación, trece líneas y una reserva del 15 %. Está implementado en Python con **Pyomo** y se resuelve
con **HiGHS**, un *solver* libre. Incluye una herramienta de apoyo a la decisión hecha con **Streamlit**.

Este repositorio acompaña a la memoria `Memoria_Caso_Red_Electrica_v10` de la asignatura *Métodos Cuantitativos
para la Organización Industrial* (Máster Universitario en Ingeniería Industrial, ETSII, UPV, curso 2026-2027).

| Caso base | Valor |
| --- | --- |
| Coste óptimo del día | 613.800 € |
| Emisiones | 27.028 t CO₂-eq |
| Tamaño del modelo | 1.105 variables (144 binarias) y 698 restricciones |
| Tiempo de resolución | menos de 1 s |
| Pruebas de verificación y validación | 14 de 14 superadas |

## 1. Instalación

Hace falta Python 3.10, 3.11 o 3.12 (HiGHS aún no tiene versión para Python más reciente).

**Windows, sin usar la terminal.** Doble clic en `EJECUTAR_HERRAMIENTA.bat`. La primera vez crea el entorno
`.venv` con Python 3.12, instala las librerías, ejecuta la validación y abre la herramienta en el navegador.

**Cualquier sistema, desde la terminal:**

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS o Linux: source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Uso con Visual Studio Code

1. Instalar [Visual Studio Code](https://code.visualstudio.com/) y la extensión **Python** de Microsoft (al
   abrir la carpeta, VS Code la propone porque está en `.vscode/extensions.json`).
2. **Archivo → Abrir carpeta…** y elegir la carpeta del repositorio (o, en GitHub, **Code → Codespaces →
   Create codespace on main**, que abre VS Code en el navegador sin instalar nada).
3. Crear el entorno: **Ctrl+Mayús+P → «Python: Create Environment» → Venv**, marcando `requirements.txt`.
   Si ya existe `.venv` (por ejemplo, creado por el `.bat`), basta con elegirlo en
   **Ctrl+Mayús+P → «Python: Select Interpreter»**.
4. Ejecutar desde la vista **Ejecutar y depurar (Ctrl+Mayús+D)**, eligiendo una de las configuraciones de
   `.vscode/launch.json`:
   - *Herramienta de apoyo a la decisión (Streamlit)*
   - *Caso base, versiones e hipótesis (cap. 7)*
   - *Verificación y validación (cap. 6)*
   - *Análisis de sensibilidad y validez (cap. 8 y 10.4)*
   - *Frontera de Pareto coste-CO2 (cap. 9)*
   - *Figuras 1 a 4 de la memoria*
5. Las pruebas aparecen en la vista **Pruebas** (icono del matraz), configurada para `pytest`.

## 3. Herramienta para el decisor

```bash
streamlit run app.py
```

Se abre en el navegador (http://localhost:8501).

1. **Barra lateral: definir el escenario.** Hipótesis de modelado (lectura de la curva nuclear, red, reserva,
   reserva hidráulica bajo 10 m, depósito, nivel inicial y final, bombeo, día cíclico), intercambio exterior
   (precios por periodo), centrales paradas y sus costes y límites, líneas cortadas y sus capacidades, parque
   eólico en lugar de la nuclear y factores de emisión.
2. **Resolver escenario.** Tarda menos de un segundo en el caso base.
3. **Pestañas de resultados:** Resumen, Despacho, Depósito y reserva, Red, Comparar escenarios, Sensibilidad
   (barre un parámetro y dibuja coste, CO₂ y demanda no servida) y Datos (descarga en Excel).

La opción «Permitir cortes de suministro» (activada por defecto) hace que un escenario imposible, como una
central averiada, no se quede sin respuesta: el modelo indica cuánta demanda no podría atenderse (penalizada
a 10.000 €/MWh) y cuánta reserva falta (1.000 €/MW·h).

## 4. Reproducir los resultados de la memoria

| Comando | Qué genera | Memoria |
| --- | --- | --- |
| `python figuras_memoria.py` | Figuras 1 a 4 (esquema del caso, demanda, red y curva nuclear) en `resultados/figuras/` | Capítulos 2 y 4 |
| `python validacion.py` | Las 14 comprobaciones de verificación y validación (registro en `registro_validacion.txt`) | Capítulo 6 |
| `python ejecutar_base.py` | Caso base (`resultados/caso_base.xlsx` y Figura 7), versiones V0 a V4 con su tamaño (`versiones_modelo.csv`, Tabla 8) y efecto de cada hipótesis (`hipotesis.csv`, Tabla 10) | Capítulo 7 |
| `python analisis_sensibilidad.py` | Análisis 1 a 5 del enunciado y condiciones de validez, en `resultados/sensibilidad/` (`a1` a `a5`, `a7_validez_demanda.csv`) | Capítulo 8 y apartado 10.4 |
| `python analisis_sensibilidad.py pareto` | Frontera de Pareto coste–CO₂ y precio del CO₂ (`a6_pareto_co2.csv` y `.png`) | Capítulo 9 |
| `pytest` | Pruebas automáticas del modelo (`tests/`) | Capítulo 6 |

El caso base tiene óptimos alternativos: con otra versión de HiGHS o en otro equipo pueden salir flujos u horas
de saturación de líneas distintos con el mismo coste. Los tiempos de resolución dependen del equipo.

## 5. Pruebas automáticas

`tests/test_modelo.py` comprueba el coste, las emisiones y el tamaño del caso base, los balances, la reserva y el
depósito, las versiones del modelo y las 14 comprobaciones de `validacion.py`. GitHub las ejecuta en cada cambio
con Python 3.10, 3.11 y 3.12 (`.github/workflows/python-package.yml`).

## 6. Ficheros

| Fichero | Contenido |
| --- | --- |
| `datos.py` | Datos del enunciado e hipótesis H1 a H9 (apartado 2.6 de la memoria), todas parametrizadas en `escenario_base()` |
| `modelo.py` | `construir_modelo(d)`, `resolver(m)`, `resultados(m, d)` y `tamano(m)`; cada restricción lleva su etiqueta (R1) a (R11) |
| `MODELO.md` | Formulación matemática (capítulo 4 de la memoria) |
| `escenarios.py` | Lógica de la herramienta: indicadores, interpretación, barridos, Excel y perfiles de viento (H9) |
| `graficos.py` | Figuras de la herramienta |
| `app.py` | Interfaz Streamlit |
| `ejecutar_base.py`, `validacion.py`, `analisis_sensibilidad.py`, `figuras_memoria.py` | Resultados, evidencias y figuras de la memoria |
| `tests/` | Pruebas automáticas (pytest) |
| `EJECUTAR_HERRAMIENTA.bat` | Instalación y arranque en Windows |
| `requirements.txt` | Librerías necesarias |
| `.vscode/` | Configuración de Visual Studio Code: intérprete, ejecución, tareas y pruebas |
| `resultados/` | Tablas y figuras generadas por los *scripts* |

## 7. Hipótesis del caso base

| Id | Hipótesis |
| --- | --- |
| H1 | Un único depósito superior compartido por B y E |
| H2 | Nivel inicial de 10 m y nivel final mayor o igual que el inicial |
| H3 | Térmicas A, C y F de ciclo combinado de gas (0,49 t CO₂/MWh) |
| H4 | El eje X de la curva de la nuclear es el coste marginal (€/MWh) |
| H5 | Día tipo cíclico: la hora 23 precede a la hora 0 |
| H6 | Bombeo sin límite propio de potencia ni exclusión con el turbinado |
| H7 | 500 MW por conexión exterior; sin intercambio en el caso base |
| H8 | Red como modelo de transporte sin pérdidas |
| H9 | Perfiles de viento ilustrativos y coste variable nulo de la eólica |

## 8. Cómo trabajamos

1. **Una rama por tarea.** No se edita `main` directamente: se crea una rama y se une con un *pull request*
   que revisa otro miembro del equipo.
2. **Commits pequeños y con mensaje claro**, que digan qué cambia.
3. **Las decisiones de modelado se dejan escritas** en el código o en el *pull request* para poder citarlas en
   la memoria.
