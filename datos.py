"""
datos.py — Datos del Caso Red Eléctrica (MCOI 2026-27) e hipótesis de modelado.

Convención (como en clase): DATOS en MAYÚSCULAS, variables en minúsculas.
Todo lo que NO viene en el enunciado está marcado con [HIPÓTESIS Hx] y es un
parámetro editable desde la herramienta (o desde `escenario_base()`).
La numeración H1–H9 es la de la memoria (apartado 2.6, Tabla 2):
  H1 depósito único compartido por B y E      H6 bombeo sin límite propio de potencia
  H2 nivel inicial 10 m y final >= inicial    H7 intercambio exterior: 500 MW por conexión
  H3 térmicas A, C y F de ciclo combinado     H8 red como modelo de transporte sin pérdidas
  H4 eje X de la curva nuclear = coste marginal   H9 perfiles de viento ilustrativos (escenarios.py)
  H5 día tipo cíclico (la hora 23 precede a la 0)
"""
import copy

# ---------------------------------------------------------------------------
# Horizonte y demanda
# ---------------------------------------------------------------------------
HORAS = list(range(24))
PERFIL = [85, 80, 76, 60, 68, 66, 72, 70, 70, 84, 70, 65,
          95, 92, 93, 83, 85, 80, 85, 86, 90, 100, 99, 80]          # % del máximo
NODOS_DEMANDA = [1, 2, 3, 4, 5]
DMAX = {1: 250, 2: 1000, 3: 825, 4: 1150, 5: 700}                  # MW

# ---------------------------------------------------------------------------
# Generación
# ---------------------------------------------------------------------------
TERMICAS = ['A', 'C', 'F']
NUCLEAR = ['D']
HIDRO = ['B', 'E']

PMAX = {'A': 1350, 'C': 700, 'F': 1050, 'D': 1000}
PMIN = {'A': 0.40 * 1350, 'C': 0.50 * 700, 'F': 0.40 * 1050, 'D': 0.50 * 1000}
CMIN = {'A': 4000, 'C': 5000, 'F': 9000, 'D': 4000}                # €/h funcionando al mínimo
CEXTRA = {'A': 5.0, 'C': 4.5, 'F': 5.0}                            # €/MWh por encima del mínimo
CARR = {'A': 3000, 'C': 2000, 'F': 1000, 'D': 3000,                # € por puesta en marcha
        'B': 2000, 'E': 2000}

PH = {'B': 450, 'E': 400}              # MW (nivel fijo de las hidráulicas)
CH = {'B': 350, 'E': 300}              # €/h
DESC = {'B': 0.30, 'E': 0.48}          # m de descenso del depósito por hora turbinando
E_BOMBEO = 3300.0                      # MWh para subir 1 m
HMIN, HMAX = 10.0, 20.0                # m

# ---------------------------------------------------------------------------
# Curva de costes extra de la nuclear D (Figura 1 del enunciado), digitalizada del PDF.
# Puntos (euros_eje_x, MW_extra_eje_y).  Digitalización automática de la imagen
# (ejes calibrados con la rejilla): error estimado ±5 MW / ±0,05 €.
# ---------------------------------------------------------------------------
CURVA_D = [(0.0, 0), (1.0, 17), (2.0, 43), (3.0, 83), (3.5, 112), (4.0, 175),
           (4.5, 318), (5.0, 377), (5.5, 409), (6.0, 424), (7.0, 452),
           (8.0, 469), (9.0, 485), (10.0, 500)]


def curva_nuclear(lectura='marginal'):
    """Devuelve los puntos de ruptura (MW_extra_k, COSTE_k) de la función de coste
    extra de la nuclear según la lectura que se haga del eje X de la Figura 1 del enunciado.

    [HIPÓTESIS H4] lecturas posibles:
      'marginal' : X = coste marginal (€/MWh) del MW extra nº Y  -> coste total = integral.
                   Curva de oferta clásica; función de coste CONVEXA (sin binarias).
      'medio'    : X = coste medio (€/MWh) de los Y MW extra     -> coste = X·Y.
      'total_k'  : X = coste total extra en k€/h para producir Y MW extra
                   -> función NO convexa (necesita SOS2 / binarias).
    """
    pts = sorted(CURVA_D, key=lambda p: p[1])
    if lectura == 'marginal':
        out, coste = [(0.0, 0.0)], 0.0
        for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
            coste += 0.5 * (x0 + x1) * (y1 - y0)          # regla del trapecio
            out.append((float(y1), coste))
        return out
    if lectura == 'medio':
        return [(float(y), x * y) for x, y in pts]
    if lectura == 'total_k':
        return [(float(y), 1000.0 * x) for x, y in pts]
    raise ValueError(lectura)


# ---------------------------------------------------------------------------
# Red (Figura 2 del enunciado).  Las centrales son nodos de la red (la línea "B1" une la
# central B con el centro de transformación 1, etc.).  [HIPÓTESIS H8] las
# centrales pueden actuar como nodos de tránsito (p. ej. 4 -> E -> 3) y el
# transporte no tiene pérdidas (modelo de transporte: no hay reactancias).
# ---------------------------------------------------------------------------
LINEAS = {  # nombre: (nodo_i, nodo_j)
    'A1': ('A', 1), 'A4': ('A', 4), 'A5': ('A', 5),
    'B1': ('B', 1), 'B2': ('B', 2),
    'C2': ('C', 2), 'C3': ('C', 3),
    'D4': ('D', 4), 'D2': ('D', 2),
    'E4': ('E', 4), 'E3': ('E', 3),
    'F5': ('F', 5), 'F3': ('F', 3),
}
CAP_LINEA = {l: 500.0 for l in LINEAS}
CAP_LINEA.update({'B1': 200.0, 'F5': 400.0, 'E4': 400.0, 'A4': 600.0})

NODOS_EXT = [1, 5]          # nodos con conexión a la red vecina


def escenario_base():
    """Diccionario con TODOS los datos e hipótesis de un escenario.
    La herramienta y los análisis de sensibilidad copian y modifican este dict."""
    return copy.deepcopy(dict(
        HORAS=HORAS, PERFIL=PERFIL, DMAX=DMAX,
        TERMICAS=TERMICAS, NUCLEAR=NUCLEAR, HIDRO=HIDRO,
        PMAX=PMAX, PMIN=PMIN, CMIN=CMIN, CEXTRA=CEXTRA, CARR=CARR,
        PH=PH, CH=CH, DESC=DESC, E_BOMBEO=E_BOMBEO, HMIN=HMIN, HMAX=HMAX,
        LINEAS=LINEAS, CAP_LINEA=CAP_LINEA, NODOS_EXT=NODOS_EXT,
        LECTURA_CURVA_D='marginal',  # [H4] el eje X de la curva del enunciado es el coste por MW extra (marginal)
        FORZAR_SOS2=False,           # usar binarias SOS2 aunque la curva sea convexa (validación)
        # --- [H1] un único depósito superior compartido por B y E
        DEPOSITO_COMPARTIDO=True,
        # --- [H2] nivel inicial: el peor caso posible, el mínimo permitido (10 m),
        #     y el día debe acabar al menos con el mismo nivel
        H0=10.0,                     # m a las 0:00
        CIERRE_DEPOSITO='>=',        # nivel a las 24:00 >= H0  ('>=', '==', 'libre')
        # --- [H6] bombeo: se hace en las propias centrales B y E. El enunciado no limita su potencia ni
        #     prohíbe bombear y turbinar a la vez: None = sin esas restricciones (lo más simple).
        #     Un dict {'B': MW, 'E': MW} activa el límite y la exclusión (versión alternativa).
        PBOMBA=None,
        # --- reserva del 15 % (enunciado): margen de las centrales en marcha + hidráulicas paradas
        #     + bombeo interrumpible
        RESERVA=0.15,
        RESERVA_MODO='sistema',      # 'sistema' (nudo único) | 'red' (con flujos factibles)
        RESERVA_HIDRO_SIN_AGUA=True, # enunciado: para la reserva se permite bajar del mínimo de 10 m
                                     # (False = la reserva hidráulica sólo cuenta si queda agua)
        # --- [H5] estado inicial: día tipo cíclico (estado a las 23h = estado previo a las 0h)
        CICLICO=True,
        U0={'A': 1, 'C': 0, 'F': 0, 'D': 1, 'B': 0, 'E': 0},   # sólo si CICLICO=False
        # --- [H7] intercambio con redes vecinas (desactivado en el caso base)
        INTERCAMBIO=False,
        CAP_EXT={1: 500.0, 5: 500.0},                     # MW por conexión externa
        PRECIO_COMPRA=[60.0] * 24,                        # €/MWh
        PRECIO_VENTA=[0.0] * 24,                          # €/MWh
        # --- centrales indisponibles (análisis 3) y líneas cortadas (análisis 4)
        INDISPONIBLES=[], LINEAS_CORTADAS=[],
        # --- análisis 5: eólica ([H9] perfiles de viento ilustrativos en escenarios.py)
        EOLICA=False, P_EOLICA=0.0, NODO_EOLICA='D', PERFIL_EOLICO=[0.0] * 24,
        C_EOLICA=0.0, CMIN_EOLICA=0.0,
        # --- [H8] modelo de red
        RED=True,                    # False = nudo único (versión V1)
        # --- penalización de demanda no servida (sólo para diagnosticar infactibilidades)
        ENS=False, C_ENS=10000.0,
        # --- [H3] factores de emisión de ciclo de vida, t CO2-eq/MWh (IPCC AR5, Anexo III, medianas).
        #     Las térmicas A, C y F se consideran de ciclo combinado de gas.
        CO2_MAX=None,                # tope de emisiones diarias, t CO2-eq (frontera de Pareto)
        PRECIO_CO2=0.0,              # €/t CO2 dentro de la función objetivo
        PESO_CO2=0.0,                # peso auxiliar para desempatar a favor de menos CO2
        EMISION={'A': 0.49, 'C': 0.49, 'F': 0.49, 'D': 0.012, 'B': 0.024, 'E': 0.024, 'Eólica': 0.011},
    ))
