"""
validacion.py — Verificación y validación del modelo (evidencias para la memoria).

V1  Comprobación a posteriori de la solución base (balances, cotas, lógica, reserva)
    con cálculos INDEPENDIENTES del modelo (se recalcula todo desde la solución).
V2  Recalcular el coste a mano y compararlo con la función objetivo.
V3  Caso de una hora resuelto por FUERZA BRUTA (2^6 combinaciones de marcha + despacho
    por orden de mérito) y comparado con el MILP.
V4  Coherencia entre versiones del modelo:
      - sin red (nudo único) debe ser <= con red          (relajación)
      - sin reserva debe ser <= con reserva               (relajación)
      - curva nuclear con SOS2 forzado == formulación convexa sin binarias
      - reserva 'red' (con flujos) debe ser >= reserva 'sistema'
"""
import itertools
import numpy as np
import pyomo.environ as pyo
from datos import escenario_base, curva_nuclear
from modelo import construir_modelo, resolver, resultados

TOL = 1e-4
informe = []


def check(nombre, ok, detalle=''):
    informe.append((nombre, bool(ok), detalle))
    print(f"[{'OK ' if ok else 'ERR'}] {nombre} {detalle}")


def coste_nuclear(extra, pts):
    xs, ys = zip(*pts)
    return float(np.interp(extra, xs, ys))


def v1_v2(d, m, r):
    M = m._meta
    T = M['T']
    gen, b, est = r['gen'], r['bombeo'], r['estado']
    # balance de sistema
    oferta = gen.sum(axis=1) - b.sum(axis=1)
    err = (oferta - r['demanda']).abs().max()
    check('V1.1 Balance de potencia del sistema en cada hora', err < 1e-3, f'(error máx {err:.2e} MW)')
    # balance nodal recomputado con los flujos
    if d['RED']:
        errn = 0
        for t in T:
            for n in M['NODOS']:
                g = gen.loc[t, n] if n in gen.columns else 0
                g -= b.loc[t, n] if n in b.columns else 0
                ent = sum(r['flujos'].loc[t, l] for l in M['L'] if d['LINEAS'][l][1] == n)
                sal = sum(r['flujos'].loc[t, l] for l in M['L'] if d['LINEAS'][l][0] == n)
                errn = max(errn, abs(g + ent - sal - M['dem'][n, t]))
        check('V1.2 Balance en cada nodo (Kirchhoff) recalculado', errn < 1e-3, f'(error máx {errn:.2e} MW)')
        exc = max(r['flujos'][l].abs().max() - d['CAP_LINEA'][l] for l in M['L'])
        check('V1.3 Flujos dentro de la capacidad de las líneas', exc < 1e-4, f'(máx exceso {exc:.2e})')
    # límites técnicos
    ok = all((gen.loc[t, g] >= d['PMIN'][g] * est.loc[t, g] - TOL) and
             (gen.loc[t, g] <= d['PMAX'][g] * est.loc[t, g] + TOL) for g in M['GTN'] for t in T)
    check('V1.4 Potencias entre mínimo y máximo técnico (0 si parada)', ok)
    if d['PBOMBA'] is not None:
        ok = all(not (est.loc[t, h] == 1 and b.loc[t, h] > TOL) for h in M['GH'] for t in T)
        check('V1.5 Ninguna hidráulica bombea y turbina a la vez', ok)
    if d['PBOMBA'] is not None and d['DEPOSITO_COMPARTIDO']:
        ok = all(not (est.loc[t, M['GH']].sum() > 0 and b.loc[t].sum() > TOL) for t in T)
        check('V1.5b No se bombea a un depósito del que otra central está turbinando', ok)
    # depósito recalculado
    h = d['H0']
    hmin = hmax = h
    for t in T:
        h += -sum(d['DESC'][g] * est.loc[t, g] for g in M['GH']) + b.loc[t].sum() / d['E_BOMBEO']
        hmin, hmax = min(hmin, h), max(hmax, h)
    check('V1.6 Nivel del depósito recalculado dentro de [10, 20] m', hmin >= d['HMIN'] - TOL and hmax <= d['HMAX'] + TOL,
          f'(min {hmin:.2f} m, max {hmax:.2f} m, final {h:.2f} m)')
    check('V1.7 Cierre del día: nivel final >= inicial', h >= d['H0'] - TOL)
    hol = (r['reserva'] - r['reserva_req']).min()
    check('V1.8 Reserva >= 15 % de la demanda en todas las horas', hol >= -TOL, f'(holgura mínima {hol:.1f} MW)')
    # arranques recalculados
    arr = 0
    for g in M['G']:
        for i, t in enumerate(T):
            prev = est.loc[T[i - 1], g] if (i > 0 or d['CICLICO']) else d['U0'].get(g, 0)
            arr += d['CARR'][g] * max(0, est.loc[t, g] - prev)
    # coste recalculado a mano
    pts = curva_nuclear(d['LECTURA_CURVA_D'])
    coste = arr
    for t in T:
        for g in M['GT']:
            coste += est.loc[t, g] * (d['CMIN'][g] + d['CEXTRA'][g] * (gen.loc[t, g] - d['PMIN'][g]))
        for g in M['GN']:
            coste += est.loc[t, g] * (d['CMIN'][g] + coste_nuclear(gen.loc[t, g] - d['PMIN'][g], pts))
        for g in M['GH']:
            coste += est.loc[t, g] * d['CH'][g]
    dif = abs(coste - r['costes']['total'])
    check('V2  Coste recalculado a mano == función objetivo', dif < 1, f'({coste:,.0f} € vs {r["costes"]["total"]:,.0f} €)')


def v3_fuerza_bruta(hora=21):
    """Una sola hora, sin red, sin agua (cierre libre): enumeración exhaustiva."""
    d = escenario_base()
    d.update(HORAS=[hora], RED=False, CIERRE_DEPOSITO='libre', H0=15.0)   # con agua disponible para turbinar
    D = sum(d['DMAX'].values()) * d['PERFIL'][hora] / 100
    pts = curva_nuclear(d['LECTURA_CURVA_D'])
    unid = ['A', 'C', 'F', 'D', 'B', 'E']
    mejor = (np.inf, None)
    for comb in itertools.product([0, 1], repeat=6):
        u = dict(zip(unid, comb))
        hidro = sum(d['PH'][h] * u[h] for h in ['B', 'E'])
        resto = D - hidro
        on = [g for g in ['A', 'C', 'F', 'D'] if u[g]]
        lo = sum(d['PMIN'][g] for g in on)
        hi = sum(d['PMAX'][g] for g in on)
        if resto < lo - 1e-9 or resto > hi + 1e-9:
            continue
        reserva = hi - resto + sum(d['PH'][h] * (1 - u[h]) for h in ['B', 'E'])
        if reserva < 0.15 * D - 1e-9:
            continue
        # tramos de coste marginal: (coste €/MW, MW disponibles) por encima de los mínimos
        tramos = [(d['CEXTRA'][g], d['PMAX'][g] - d['PMIN'][g]) for g in on if g != 'D']
        if u['D']:
            tramos += [((c1 - c0) / (y1 - y0), y1 - y0) for (y0, c0), (y1, c1) in zip(pts[:-1], pts[1:])]
        falta, cvar = resto - lo, 0.0
        for c, cap in sorted(tramos):
            q = min(cap, falta)
            cvar += c * q
            falta -= q
        coste = sum(d['CMIN'][g] for g in on) + sum(d['CH'][h] * u[h] for h in ['B', 'E']) + cvar
        if coste < mejor[0]:
            mejor = (coste, u)
    m = construir_modelo(d)
    resolver(m)
    z = pyo.value(m.obj)
    check(f'V3  Hora {hora} por fuerza bruta (64 combinaciones) == MILP', abs(z - mejor[0]) < 1,
          f'({mejor[0]:,.1f} € vs {z:,.1f} €; marcha {"".join(k for k, v in mejor[1].items() if v)})')


def v4_versiones(z_base):
    def coste(**cambios):
        d = escenario_base()
        d.update(cambios)
        m = construir_modelo(d)
        info = resolver(m)
        return info['coste']
    z = coste(RED=False)
    check('V4.1 Sin red (nudo único) <= con red', z <= z_base + 1, f'({z:,.0f} € vs {z_base:,.0f} €; la red encarece {z_base - z:,.0f} €)')
    z = coste(RESERVA=0)
    check('V4.2 Sin reserva <= con reserva', z <= z_base + 1, f'({z:,.0f} €)')
    z = coste(FORZAR_SOS2=True)
    check('V4.3 Nuclear con SOS2 (binarias) == formulación convexa', abs(z - z_base) < 1, f'({z:,.0f} €)')
    z = coste(RESERVA_MODO='red')
    check('V4.4 Reserva con red >= reserva de sistema', z >= z_base - 1, f'({z:,.0f} €)')


if __name__ == '__main__':
    d = escenario_base()
    m = construir_modelo(d)
    info = resolver(m)
    print(info)
    r = resultados(m, d)
    v1_v2(d, m, r)
    v3_fuerza_bruta(21)
    v3_fuerza_bruta(3)
    v4_versiones(r['costes']['total'])
    n_ok = sum(ok for _, ok, _ in informe)
    print(f'\n{n_ok}/{len(informe)} comprobaciones superadas')
