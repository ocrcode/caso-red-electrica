"""
modelo.py — Modelo MILP de programación de la generación (Unit Commitment con red,
bombeo y reserva) para el Caso Red Eléctrica, implementado en Pyomo.

Uso:
    from datos import escenario_base
    from modelo import construir_modelo, resolver, resultados
    d = escenario_base()
    m = construir_modelo(d)
    info = resolver(m)
    r = resultados(m, d)

Notación: la del capítulo 4 de la memoria (DATOS en mayúsculas, variables en minúsculas).
  Conjuntos  T horas, N nodos de red, L líneas, GT térmicas, GN nuclear, GH hidráulicas,
             K puntos de ruptura de la curva de la nuclear, R depósitos (uno si se comparte, H1).
  Variables  u[g,t] marcha (bin), s[g,t] arranque, p[g,t] potencia, lam[g,k,t] pesos de la
             curva nuclear, z[g,k,t] segmento activo (bin, solo si la curva no es convexa),
             w[h,t] modo bombeo (bin, solo versión V4), b[h,t] potencia de bombeo,
             niv[r,tau] nivel del depósito, f[l,t] flujo por línea, c/v[n,t] compra/venta,
             pe[t] producción eólica (análisis 5), ens[n,t] y rdef[t] diagnóstico (R10).
  Restricciones: los comentarios (R1)…(R11) siguen la numeración de la memoria.
"""
import pyomo.environ as pyo
from datos import curva_nuclear


def _es_convexa(puntos):
    """True si la función lineal a tramos (x_k, y_k) es convexa (pendientes crecientes)."""
    pend = [(y1 - y0) / (x1 - x0) for (x0, y0), (x1, y1) in zip(puntos[:-1], puntos[1:])]
    return all(p1 >= p0 - 1e-9 for p0, p1 in zip(pend[:-1], pend[1:]))


def construir_modelo(d):
    m = pyo.ConcreteModel('RedElectrica')

    # ------------------------------------------------------------------ CONJUNTOS
    T = list(d['HORAS'])
    GT = [g for g in d['TERMICAS'] if g not in d['INDISPONIBLES']]
    GN = [g for g in d['NUCLEAR'] if g not in d['INDISPONIBLES'] and not d['EOLICA']]
    GH = [g for g in d['HIDRO'] if g not in d['INDISPONIBLES']]
    GTN = GT + GN                                  # centrales con rango [PMIN, PMAX]
    G = GTN + GH                                   # centrales con decisión de marcha
    NODOS = list(d['DMAX'].keys()) + d['TERMICAS'] + d['NUCLEAR'] + d['HIDRO']
    L = [l for l in d['LINEAS'] if l not in d['LINEAS_CORTADAS']]
    NEXT = list(d['NODOS_EXT']) if d['INTERCAMBIO'] else []
    RES = ['S'] if d['DEPOSITO_COMPARTIDO'] else list(d['HIDRO'])   # depósitos
    res_de = {h: ('S' if d['DEPOSITO_COMPARTIDO'] else h) for h in d['HIDRO']}
    TT = T + [T[-1] + 1]                           # instantes 0..24 para el nivel

    pts = curva_nuclear(d['LECTURA_CURVA_D'])
    K = list(range(len(pts)))
    convexa = _es_convexa(pts) and not d.get('FORZAR_SOS2', False)

    m.T = pyo.Set(initialize=T, ordered=True)
    m.TT = pyo.Set(initialize=TT, ordered=True)
    m.GT = pyo.Set(initialize=GT)
    m.GN = pyo.Set(initialize=GN)
    m.GTN = pyo.Set(initialize=GTN)
    m.GH = pyo.Set(initialize=GH)
    m.G = pyo.Set(initialize=G)
    m.N = pyo.Set(initialize=NODOS)
    m.L = pyo.Set(initialize=L)
    m.NEXT = pyo.Set(initialize=NEXT)
    m.R = pyo.Set(initialize=RES)
    m.K = pyo.Set(initialize=K, ordered=True)
    m.KS = pyo.Set(initialize=K[1:], ordered=True)         # segmentos k = (k-1, k)

    # ------------------------------------------------------------------ PARÁMETROS
    dem = {(n, t): d['DMAX'].get(n, 0.0) * d['PERFIL'][t] / 100.0 for n in NODOS for t in T}
    m.DEM = pyo.Param(m.N, m.T, initialize=dem)
    m.PMAX = pyo.Param(m.GTN, initialize={g: d['PMAX'][g] for g in GTN})
    m.PMIN = pyo.Param(m.GTN, initialize={g: d['PMIN'][g] for g in GTN})
    m.CMIN = pyo.Param(m.GTN, initialize={g: d['CMIN'][g] for g in GTN})
    m.CEXTRA = pyo.Param(m.GT, initialize={g: d['CEXTRA'][g] for g in GT})
    m.CARR = pyo.Param(m.G, initialize={g: d['CARR'][g] for g in G})
    m.PH = pyo.Param(m.GH, initialize={g: d['PH'][g] for g in GH})
    m.CH = pyo.Param(m.GH, initialize={g: d['CH'][g] for g in GH})
    m.DESC = pyo.Param(m.GH, initialize={g: d['DESC'][g] for g in GH})
    if d['PBOMBA'] is not None:
        m.PBOMBA = pyo.Param(m.GH, initialize={g: d['PBOMBA'][g] for g in GH})
    m.YD = pyo.Param(m.K, initialize={k: pts[k][0] for k in K})        # MW extra
    m.CD = pyo.Param(m.K, initialize={k: pts[k][1] for k in K})        # € extra/h
    m.CAP = pyo.Param(m.L, initialize={l: d['CAP_LINEA'][l] for l in L})
    m.PC = pyo.Param(m.T, initialize={t: d['PRECIO_COMPRA'][t] for t in T})
    m.PV = pyo.Param(m.T, initialize={t: d['PRECIO_VENTA'][t] for t in T})

    def prev(t):
        return T[(T.index(t) - 1) % len(T)]

    # ------------------------------------------------------------------ VARIABLES
    m.u = pyo.Var(m.G, m.T, domain=pyo.Binary)                       # en marcha
    m.s = pyo.Var(m.G, m.T, bounds=(0, 1))                           # arranque (relajada: es integral por construcción)
    m.p = pyo.Var(m.GTN, m.T, domain=pyo.NonNegativeReals)           # potencia térmica/nuclear
    m.lam = pyo.Var(m.GN, m.K, m.T, domain=pyo.NonNegativeReals)     # pesos de la curva nuclear
    if not convexa:
        m.z = pyo.Var(m.GN, m.KS, m.T, domain=pyo.Binary)            # SOS2 con binarias (segmento activo)
    if d['PBOMBA'] is not None:
        m.w = pyo.Var(m.GH, m.T, domain=pyo.Binary)                  # bombeando (sólo si se limita el bombeo)
    m.b = pyo.Var(m.GH, m.T, domain=pyo.NonNegativeReals)            # potencia de bombeo
    m.niv = pyo.Var(m.R, m.TT, bounds=(d['HMIN'], d['HMAX']))        # nivel del depósito (m), R6
    # (R8) Capacidad de líneas e intercambio: se imponen como cotas de f, c y v (no añaden filas)
    m.f = pyo.Var(m.L, m.T, bounds=lambda m, l, t: (-m.CAP[l], m.CAP[l]))   # flujo i->j (signo libre)
    m.c = pyo.Var(m.NEXT, m.T, bounds=lambda m, n, t: (0, d['CAP_EXT'][n]))  # compra
    m.v = pyo.Var(m.NEXT, m.T, bounds=lambda m, n, t: (0, d['CAP_EXT'][n]))  # venta
    if d['EOLICA']:
        # (R11) Eólica (análisis 5): 0 <= pe_t <= PEOL·FV_t; lo que no se usa se vierte
        m.pe = pyo.Var(m.T, bounds=lambda m, t: (0, d['P_EOLICA'] * d['PERFIL_EOLICO'][t]))
    if d['ENS']:  # (R10) diagnóstico de escenarios imposibles
        m.ND = pyo.Set(initialize=list(d['DMAX'].keys()))
        m.ens = pyo.Var(m.ND, m.T, domain=pyo.NonNegativeReals)      # energía no servida (centros)
        m.rdef = pyo.Var(m.T, domain=pyo.NonNegativeReals)           # déficit de reserva (MW)

    # ------------------------------------------------------------------ EXPRESIONES
    def gen_nodo(m, n, t):
        e = 0
        if n in GTN:
            e = e + m.p[n, t]
        if n in GH:
            e = e + m.PH[n] * m.u[n, t] - m.b[n, t]
        if d['EOLICA'] and n == d['NODO_EOLICA']:
            e = e + m.pe[t]
        if n in NEXT:
            e = e + m.c[n, t] - m.v[n, t]
        if d['ENS'] and n in d['DMAX']:
            e = e + m.ens[n, t]
        return e
    m.gen_nodo = pyo.Expression(m.N, m.T, rule=gen_nodo)

    # ------------------------------------------------------------------ RESTRICCIONES
    # (R1) Balance de potencia en cada nodo (ley de Kirchhoff de corrientes, modelo de transporte)
    if d['RED']:
        def balance(m, n, t):
            entra = sum(m.f[l, t] for l in L if d['LINEAS'][l][1] == n)
            sale = sum(m.f[l, t] for l in L if d['LINEAS'][l][0] == n)
            return m.gen_nodo[n, t] + entra - sale == m.DEM[n, t]
        m.balance = pyo.Constraint(m.N, m.T, rule=balance)
    else:  # validación: sistema de nudo único (sin red)
        m.balance = pyo.Constraint(m.T, rule=lambda m, t:
                                   sum(m.gen_nodo[n, t] for n in NODOS) == sum(m.DEM[n, t] for n in NODOS))

    # (R2) Límites técnicos condicionados a la marcha
    m.pmin = pyo.Constraint(m.GTN, m.T, rule=lambda m, g, t: m.p[g, t] >= m.PMIN[g] * m.u[g, t])
    m.pmax = pyo.Constraint(m.GTN, m.T, rule=lambda m, g, t: m.p[g, t] <= m.PMAX[g] * m.u[g, t])

    # (R3) Arranques: s >= u_t - u_{t-1} (t-1 cíclico si CICLICO, H5)
    def arranque(m, g, t):
        if t == T[0] and not d['CICLICO']:
            return m.s[g, t] >= m.u[g, t] - d['U0'].get(g, 0)
        return m.s[g, t] >= m.u[g, t] - m.u[g, prev(t)]
    m.arranque = pyo.Constraint(m.G, m.T, rule=arranque)

    # (R4) Nuclear: curva de coste extra lineal a tramos (formulación lambda)
    m.nuc_p = pyo.Constraint(m.GN, m.T, rule=lambda m, g, t:
                             m.p[g, t] == m.PMIN[g] * m.u[g, t] + sum(m.YD[k] * m.lam[g, k, t] for k in K))
    m.nuc_conv = pyo.Constraint(m.GN, m.T, rule=lambda m, g, t:
                                sum(m.lam[g, k, t] for k in K) == m.u[g, t])
    if not convexa:  # SOS2 con binarias: sólo dos lambdas adyacentes no nulas
        m.sos2_z = pyo.Constraint(m.GN, m.T, rule=lambda m, g, t:
                                  sum(m.z[g, k, t] for k in K[1:]) == m.u[g, t])

        def sos2_lam(m, g, k, t):
            e = 0
            if k >= 1:
                e = e + m.z[g, k, t]
            if k + 1 <= K[-1]:
                e = e + m.z[g, k + 1, t]
            return m.lam[g, k, t] <= e
        m.sos2_lam = pyo.Constraint(m.GN, m.K, m.T, rule=sos2_lam)

    # (R5) Bombeo. Caso base (PBOMBA=None): el enunciado no limita la potencia de bombeo ni prohíbe
    #     bombear y turbinar a la vez, así que sólo lo limitan las líneas que llegan a B y E.
    #     Versión alternativa (PBOMBA={...}): potencia máxima de bombeo y no bombear mientras se turbina.
    if d['PBOMBA'] is not None:
        m.modo = pyo.Constraint(m.GH, m.T, rule=lambda m, g, t: m.u[g, t] + m.w[g, t] <= 1)
        m.bmax = pyo.Constraint(m.GH, m.T, rule=lambda m, g, t: m.b[g, t] <= m.PBOMBA[g] * m.w[g, t])
    if d['PBOMBA'] is not None and d['DEPOSITO_COMPARTIDO'] and len(GH) == 2:
        h1, h2 = GH
        m.cruce1 = pyo.Constraint(m.T, rule=lambda m, t: m.w[h1, t] + m.u[h2, t] <= 1)
        m.cruce2 = pyo.Constraint(m.T, rule=lambda m, t: m.w[h2, t] + m.u[h1, t] <= 1)

    # (R6) Balance del depósito superior (m de agua)
    def deposito(m, r, tt):
        if tt == TT[0]:
            return pyo.Constraint.Skip
        t = tt - 1
        hs = [g for g in GH if res_de[g] == r]
        return m.niv[r, tt] == m.niv[r, t] - sum(m.DESC[g] * m.u[g, t] for g in hs) \
            + sum(m.b[g, t] for g in hs) / d['E_BOMBEO']
    m.deposito = pyo.Constraint(m.R, m.TT, rule=deposito)
    m.niv_ini = pyo.Constraint(m.R, rule=lambda m, r: m.niv[r, TT[0]] == d['H0'])
    if d['CIERRE_DEPOSITO'] == '>=':
        m.niv_fin = pyo.Constraint(m.R, rule=lambda m, r: m.niv[r, TT[-1]] >= d['H0'])
    elif d['CIERRE_DEPOSITO'] == '==':
        m.niv_fin = pyo.Constraint(m.R, rule=lambda m, r: m.niv[r, TT[-1]] == d['H0'])

    # (R7) Reserva: poder atender en cualquier hora un incremento del RESERVA·demanda
    dtot = {t: sum(dem[n, t] for n in NODOS) for t in T}
    if d['RESERVA'] > 0 and d['RESERVA_MODO'] == 'sistema':
        if not d['RESERVA_HIDRO_SIN_AGUA']:
            # la reserva hidráulica sólo cuenta si queda agua para turbinar una hora más
            m.rh = pyo.Var(m.GH, m.T, domain=pyo.NonNegativeReals)
            m.rh1 = pyo.Constraint(m.GH, m.T, rule=lambda m, g, t: m.rh[g, t] <= m.PH[g] * (1 - m.u[g, t]))
            m.rh2 = pyo.Constraint(m.GH, m.T, rule=lambda m, g, t:
                                   m.rh[g, t] <= m.PH[g] * (m.niv[res_de[g], t + 1] - d['HMIN']) / m.DESC[g])
            reserva_h = lambda m, t: sum(m.rh[g, t] for g in GH)
        else:
            reserva_h = lambda m, t: sum(m.PH[g] * (1 - m.u[g, t]) for g in GH)
        m.reserva = pyo.Constraint(m.T, rule=lambda m, t:
                                   sum(m.PMAX[g] * m.u[g, t] - m.p[g, t] for g in GTN)
                                   + reserva_h(m, t) + sum(m.b[g, t] for g in GH)
                                   + (m.rdef[t] if d['ENS'] else 0)
                                   >= d['RESERVA'] * dtot[t])
    elif d['RESERVA'] > 0 and d['RESERVA_MODO'] == 'red':
        # Escenario de estrés: demanda ×(1+RESERVA) en todos los nodos; debe existir un
        # redespacho factible con las centrales ya encendidas (subiendo), arrancando
        # hidráulicas, parando el bombeo y respetando la capacidad de las líneas.
        m.pr = pyo.Var(m.GTN, m.T, domain=pyo.NonNegativeReals)
        m.hr = pyo.Var(m.GH, m.T, domain=pyo.NonNegativeReals)
        m.fr = pyo.Var(m.L, m.T, bounds=lambda m, l, t: (-m.CAP[l], m.CAP[l]))
        m.r_lo = pyo.Constraint(m.GTN, m.T, rule=lambda m, g, t: m.pr[g, t] >= m.p[g, t])
        m.r_hi = pyo.Constraint(m.GTN, m.T, rule=lambda m, g, t: m.pr[g, t] <= m.PMAX[g] * m.u[g, t])
        m.r_h_lo = pyo.Constraint(m.GH, m.T, rule=lambda m, g, t: m.hr[g, t] >= m.PH[g] * m.u[g, t])
        m.r_h_hi = pyo.Constraint(m.GH, m.T, rule=lambda m, g, t: m.hr[g, t] <= m.PH[g])

        def bal_r(m, n, t):
            g = 0
            if n in GTN:
                g = g + m.pr[n, t]
            if n in GH:
                g = g + m.hr[n, t]
            if d['EOLICA'] and n == d['NODO_EOLICA']:
                g = g + m.pe[t]
            if n in NEXT:
                g = g + m.c[n, t] - m.v[n, t]
            if d['ENS'] and n in d['DMAX']:
                g = g + m.ensr[n, t]
            entra = sum(m.fr[l, t] for l in L if d['LINEAS'][l][1] == n)
            sale = sum(m.fr[l, t] for l in L if d['LINEAS'][l][0] == n)
            return g + entra - sale == (1 + d['RESERVA']) * m.DEM[n, t]
        if d['ENS']:
            m.ensr = pyo.Var(m.ND, m.T, domain=pyo.NonNegativeReals)  # parte de la reserva no entregable
            m.rdef_r = pyo.Constraint(m.T, rule=lambda m, t: m.rdef[t] == sum(m.ensr[n, t] for n in m.ND))
        m.bal_r = pyo.Constraint(m.N, m.T, rule=bal_r)

    # ------------------------------------------------------------------ FUNCIÓN OBJETIVO
    m.c_fijo = pyo.Expression(expr=sum(m.CMIN[g] * m.u[g, t] for g in GTN for t in T)
                              + sum(m.CH[g] * m.u[g, t] for g in GH for t in T)
                              + (d['CMIN_EOLICA'] * len(T) if d['EOLICA'] else 0))
    m.c_var = pyo.Expression(expr=sum(m.CEXTRA[g] * (m.p[g, t] - m.PMIN[g] * m.u[g, t]) for g in GT for t in T)
                             + sum(m.CD[k] * m.lam[g, k, t] for g in GN for k in K for t in T)
                             + (sum(d['C_EOLICA'] * m.pe[t] for t in T) if d['EOLICA'] else 0))
    m.c_arr = pyo.Expression(expr=sum(m.CARR[g] * m.s[g, t] for g in G for t in T))
    m.c_ext = pyo.Expression(expr=sum(m.PC[t] * m.c[n, t] - m.PV[t] * m.v[n, t] for n in NEXT for t in T))
    m.c_ens = pyo.Expression(expr=(sum(d['C_ENS'] * m.ens[n, t] for n in m.ND for t in T)
                                   + sum(d['C_ENS'] / 10 * m.rdef[t] for t in T)) if d['ENS'] else 0)
    # (R9) Emisiones (t CO2-eq): energía producida por cada central x factor de emisión (H3)
    EM = d['EMISION']
    m.emis = pyo.Expression(expr=sum(EM.get(g, 0) * m.p[g, t] for g in GTN for t in T)
                            + sum(EM.get(g, 0) * m.PH[g] * m.u[g, t] for g in GH for t in T)
                            + (sum(EM.get('Eólica', 0) * m.pe[t] for t in T) if d['EOLICA'] else 0))
    # Método de las restricciones (épsilon): tope de emisiones diarias
    if d.get('CO2_MAX') is not None:
        m.tope_co2 = pyo.Constraint(expr=m.emis <= d['CO2_MAX'])
    # Precio del CO2 (€/t) dentro del objetivo (0 en el caso base)
    m.c_co2 = pyo.Expression(expr=d.get('PRECIO_CO2', 0.0) * m.emis)
    # Peso pequeño de las emisiones para minimizar CO2 a coste dado (lexicográfico aproximado)
    m.obj = pyo.Objective(expr=m.c_fijo + m.c_var + m.c_arr + m.c_ext + m.c_ens + m.c_co2
                          + d.get('PESO_CO2', 0.0) * m.emis, sense=pyo.minimize)

    # metadatos útiles para el post-proceso
    m._meta = dict(T=T, GT=GT, GN=GN, GH=GH, GTN=GTN, G=G, NODOS=NODOS, L=L, NEXT=NEXT,
                   RES=RES, TT=TT, dem=dem, dtot=dtot, convexa=convexa, pts=pts)
    return m


def tamano(m):
    """Tamaño del modelo: variables, variables binarias y restricciones activas (Tabla 7 de la memoria)."""
    vs = list(m.component_data_objects(pyo.Var))
    return dict(variables=len(vs), binarias=sum(1 for v in vs if v.is_binary()),
                restricciones=len(list(m.component_data_objects(pyo.Constraint, active=True))))


SOLVERS = ['appsi_highs', 'highs', 'gurobi', 'cplex', 'cbc', 'glpk']


def resolver(m, solver=None, tiempo=120, gap=1e-6, tee=False):
    """Resuelve con el primer solver disponible de la lista (o el indicado)."""
    candidatos = [solver] if solver else SOLVERS
    for nombre in candidatos:
        try:
            opt = pyo.SolverFactory(nombre)
            try:
                ok = opt.available(exception_flag=False)
            except TypeError:
                ok = opt.available()
            if not ok:
                continue
        except Exception:
            continue
        if 'highs' in nombre:
            opt.options['time_limit'] = tiempo
            opt.options['mip_rel_gap'] = gap
        elif nombre == 'cbc':
            opt.options['seconds'] = tiempo
            opt.options['ratioGap'] = gap
        elif nombre == 'glpk':
            opt.options['tmlim'] = tiempo
            opt.options['mipgap'] = gap
        res = opt.solve(m, tee=tee)
        return dict(solver=nombre, estado=str(res.solver.termination_condition),
                    coste=pyo.value(m.obj) if str(res.solver.termination_condition) in ('optimal', 'maxTimeLimit') else None)
    raise RuntimeError('No hay ningún solver disponible. Instale HiGHS:  pip install highspy')


def resultados(m, d):
    """Extrae la solución en tablas (pandas) para informes y para la herramienta."""
    import pandas as pd
    M = m._meta
    T = M['T']
    v = pyo.value
    gen = pd.DataFrame(index=T)
    for g in M['GTN']:
        gen[g] = [v(m.p[g, t]) for t in T]
    for g in M['GH']:
        gen[g] = [d['PH'][g] * round(v(m.u[g, t])) for t in T]
    if d['EOLICA']:
        gen['Eólica'] = [v(m.pe[t]) for t in T]
    for n in M['NEXT']:
        gen[f'Compra{n}'] = [v(m.c[n, t]) for t in T]
        gen[f'Venta{n}'] = [-v(m.v[n, t]) for t in T]
    bombeo = pd.DataFrame({g: [v(m.b[g, t]) for t in T] for g in M['GH']}, index=T)
    estado = pd.DataFrame({g: [round(v(m.u[g, t])) for t in T] for g in M['G']}, index=T)
    arranques = pd.DataFrame({g: [round(v(m.s[g, t])) for t in T] for g in M['G']}, index=T)
    nivel = pd.DataFrame({r: [v(m.niv[r, tt]) for tt in M['TT']] for r in M['RES']}, index=M['TT'])
    flujos = pd.DataFrame({l: [v(m.f[l, t]) for t in T] for l in M['L']}, index=T) if d['RED'] else pd.DataFrame(index=T)
    uso_lineas = flujos.abs().div(pd.Series({l: d['CAP_LINEA'][l] for l in flujos.columns})) if d['RED'] else flujos
    demanda = pd.Series([M['dtot'][t] for t in T], index=T)
    reserva = pd.Series([sum(d['PMAX'][g] * round(v(m.u[g, t])) - v(m.p[g, t]) for g in M['GTN'])
                         + sum(d['PH'][g] * (1 - round(v(m.u[g, t]))) + v(m.b[g, t]) for g in M['GH'])
                         for t in T], index=T)
    costes = dict(total=v(m.obj), fijo=v(m.c_fijo), variable=v(m.c_var),
                  arranque=v(m.c_arr), intercambio=v(m.c_ext), ens=v(m.c_ens),
                  co2=v(m.c_co2), peso_co2=d.get('PESO_CO2', 0.0) * v(m.emis), emis_t=v(m.emis))
    ens = (pd.DataFrame({n: [v(m.ens[n, t]) for t in T] for n in d['DMAX']}, index=T)
           if d['ENS'] else pd.DataFrame(index=T))
    deficit_reserva = (pd.Series([v(m.rdef[t]) for t in T], index=T) if d['ENS']
                       else pd.Series(0.0, index=T))
    return dict(gen=gen, bombeo=bombeo, estado=estado, arranques=arranques, nivel=nivel, ens=ens, deficit_reserva=deficit_reserva,
                flujos=flujos, uso_lineas=uso_lineas, demanda=demanda, reserva=reserva,
                reserva_req=d['RESERVA'] * demanda, costes=costes)
