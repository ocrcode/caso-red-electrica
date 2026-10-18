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
    """Devuelve un diccionario con los datos del enunciado.

    TODO: centrales (potencias mín./máx., costes, arranques), demanda horaria,
    líneas y capacidades, depósito de bombeo y porcentaje de reserva.
    """
    datos = {
        "horas": [],
        "centrales": [],
        "nudos": [],
        "lineas": [],
        "demanda": {},
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

    if not datos["horas"]:
        print("Esqueleto listo: faltan los datos y el modelo (ver los TODO).")
        print(f"Solver '{SOLVER}' disponible: {pyo.SolverFactory(SOLVER).available()}")
    else:
        resultado = resolver(modelo)
        mostrar_resultados(modelo, resultado)
