"""
Caso Red Eléctrica · MCOI (UPV)

Modelo de unit commitment con red, bombeo y reserva, en Pyomo y resuelto con HiGHS.

Estructura:
    1. cargar_datos()        -> parámetros del enunciado
    2. construir_modelo()    -> conjuntos, variables, restricciones y objetivo
    3. resolver()            -> llamada al solver
    4. mostrar_resultados()  -> tablas y comprobaciones

Ejecutar:  python modelo_uc.py
"""

import pyomo.environ as pyo

SOLVER = "appsi_highs"  # HiGHS a través del paquete highspy


# ---------------------------------------------------------------------------
# 1. Datos
# ---------------------------------------------------------------------------
def cargar_datos():
    """Devuelve un diccionario con los datos del enunciado (apartado 2.1).

    Unidades: potencias en MW, energías en MWh, costes en €, niveles en metros.
    Los datos que el enunciado NO da se dejan a None en `hipotesis` y deben
    fijarse (y justificarse en la memoria) antes de resolver.
    """
    # --- Demanda -------------------------------------------------------------
    horas = list(range(24))
    # % sobre el consumo máximo diario previsto, hora 0..23 (igual en todos los centros)
    perfil_pct = [85, 80, 76, 60, 68, 66, 72, 70, 70, 84, 70, 65,
                  95, 92, 93, 83, 85, 80, 85, 86, 90, 100, 99, 80]
    centros = [1, 2, 3, 4, 5]  # centros de transformación de alta tensión
    demanda_max = {1: 250, 2: 1000, 3: 825, 4: 1150, 5: 700}  # MW
    demanda = {(n, t): demanda_max[n] * perfil_pct[t] / 100
               for n in centros for t in horas}

    # --- Centrales -----------------------------------------------------------
    termicas = ["A", "C", "F"]
    hidraulicas = ["B", "E"]
    nucleares = ["D"]
    centrales = ["A", "B", "C", "D", "E", "F"]

    # Térmicas y nuclear: trabajan entre un mínimo (% del máximo) y un máximo.
    p_max = {"A": 1350, "C": 700, "F": 1050, "D": 1000}  # MW
    p_min = {"A": 0.40 * 1350, "C": 0.50 * 700, "F": 0.40 * 1050,
             "D": 0.50 * 1000}  # MW
    coste_min = {"A": 4000, "C": 5000, "F": 9000, "D": 4000}  # €/h trabajando al mínimo
    coste_extra = {"A": 5, "C": 4.5, "F": 5}  # €/MWh por encima del mínimo (D: ver curva)

    # Hidroeléctricas: producción fija cuando están en marcha.
    p_hidro = {"B": 450, "E": 400}  # MW
    coste_hora_hidro = {"B": 350, "E": 300}  # €/h
    descenso_deposito = {"B": 0.30, "E": 0.48}  # m/h turbinando

    coste_arranque = {"A": 3000, "B": 2000, "C": 2000, "D": 3000,
                      "E": 2000, "F": 1000}  # €

    # Curva de costes extra de la nuclear D (Figura 1), leída a ojo de la gráfica.
    # Pares (eje «€», MW extra sobre el mínimo). Valores aproximados.
    # HIPÓTESIS a documentar: se interpreta el eje «€» como coste marginal
    # (€/MW) del MW extra; como la curva es creciente, el coste total es convexo
    # y se puede linealizar por tramos sin binarias.
    curva_nuclear = [(0, 0), (1, 20), (2, 40), (3, 75), (3.5, 110), (4, 200),
                     (4.5, 330), (5, 385), (6, 425), (7, 450), (8, 470),
                     (9, 485), (10, 500)]

    # --- Depósito y bombeo ---------------------------------------------------
    deposito_min = 10  # m (razones medioambientales)
    deposito_max = 20  # m
    energia_bombeo_por_m = 3300  # MWh para subir 1 m de agua
    reserva = 0.15  # margen sobre la demanda prevista que debe poder cubrirse

    # --- Red (Figura 2) ------------------------------------------------------
    # Cada central es un nudo de la red; las líneas se nombran como en el
    # enunciado (central + centro). Se tratan como no dirigidas.
    nudos = centros + centrales
    lineas = {
        "A1": ("A", 1), "A4": ("A", 4), "A5": ("A", 5),
        "B1": ("B", 1), "B2": ("B", 2),
        "C2": ("C", 2), "C3": ("C", 3),
        "D2": ("D", 2), "D4": ("D", 4),
        "E3": ("E", 3), "E4": ("E", 4),
        "F3": ("F", 3), "F5": ("F", 5),
    }
    capacidad_linea = {l: 500 for l in lineas}  # MW por defecto
    capacidad_linea.update({"B1": 200, "F5": 400, "E4": 400, "A4": 600})

    # Centros que pueden comprar a la red externa.
    centros_externos = [1, 5]

    # --- Datos que el enunciado no da ----------------------------------------
    hipotesis = {
        "nivel_inicial_deposito": None,  # m; ¿y nivel final (día cíclico)?
        "deposito_compartido": True,     # ¿un único depósito para B y E?
        "precio_compra_externa": None,   # €/MWh (por hora si se quiere)
        "precio_venta_externa": None,    # €/MWh
        "capacidad_externa": None,       # MW por centro externo
        "estado_inicial": None,          # dict central -> 0/1 en la hora -1
    }

    datos = {
        "horas": horas,
        "perfil_pct": perfil_pct,
        "centros": centros,
        "demanda_max": demanda_max,
        "demanda": demanda,
        "centrales": centrales,
        "termicas": termicas,
        "hidraulicas": hidraulicas,
        "nucleares": nucleares,
        "p_max": p_max,
        "p_min": p_min,
        "coste_min": coste_min,
        "coste_extra": coste_extra,
        "p_hidro": p_hidro,
        "coste_hora_hidro": coste_hora_hidro,
        "descenso_deposito": descenso_deposito,
        "coste_arranque": coste_arranque,
        "curva_nuclear": curva_nuclear,
        "deposito_min": deposito_min,
        "deposito_max": deposito_max,
        "energia_bombeo_por_m": energia_bombeo_por_m,
        "reserva": reserva,
        "nudos": nudos,
        "lineas": lineas,
        "capacidad_linea": capacidad_linea,
        "centros_externos": centros_externos,
        "hipotesis": hipotesis,
    }
    return datos


# ---------------------------------------------------------------------------
# 2. Modelo
# ---------------------------------------------------------------------------
def construir_modelo(datos):
    """Crea el modelo de Pyomo a partir de los datos."""
    m = pyo.ConcreteModel(name="Caso Red Eléctrica")

    # Conjuntos
    m.T = pyo.Set(initialize=datos["horas"], ordered=True)
    m.G = pyo.Set(initialize=datos["centrales"])

    # TODO: parámetros, variables (u[g,t] binaria, p[g,t] potencia, flujos,
    # bombeo/turbinado, nivel del depósito), restricciones y función objetivo.

    return m


# ---------------------------------------------------------------------------
# 3. Resolución
# ---------------------------------------------------------------------------
def resolver(m):
    solver = pyo.SolverFactory(SOLVER)
    if not solver.available():
        raise RuntimeError(
            f"El solver '{SOLVER}' no está disponible. "
            "Instalad los paquetes con: pip install -r requirements.txt"
        )
    return solver.solve(m)


# ---------------------------------------------------------------------------
# 4. Resultados
# ---------------------------------------------------------------------------
def mostrar_resultados(m, resultado):
    print(resultado.solver.termination_condition)
    # TODO: coste total, programa horario por central, flujos por línea,
    # nivel del depósito y comprobación de la reserva.


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    datos = cargar_datos()
    modelo = construir_modelo(datos)

    if not list(modelo.component_objects(pyo.Objective)):
        print("Datos cargados: falta el modelo (ver los TODO).")
        print(f"Solver '{SOLVER}' disponible: {pyo.SolverFactory(SOLVER).available()}")
    else:
        resultado = resolver(modelo)
        mostrar_resultados(modelo, resultado)
