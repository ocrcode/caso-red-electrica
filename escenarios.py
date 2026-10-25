"""
escenarios.py — Lógica de la herramienta de apoyo a la decisión (sin interfaz).

Separa el cálculo de la interfaz (app.py) para que se pueda probar y reutilizar:
  resolver_escenario(d)      -> resuelve un escenario y devuelve resultados + indicadores
  indicadores(d, r)          -> KPIs del escenario (coste, CO2, arranques, ENS, líneas...)
  interpretar(d, r, k, kb)   -> frases en lenguaje llano para el decisor
  barrido(d, parametro, vals)-> análisis de sensibilidad de un parámetro
  a_excel(d, r, k)           -> bytes de un Excel con todas las tablas
"""
import copy
import io
import numpy as np
import pandas as pd

from datos import escenario_base
from modelo import construir_modelo, resolver, resultados

TRAMOS = {  # horas de cada periodo tarifario (para precios de intercambio)
    'Valle (0-7 h)': list(range(0, 8)),
    'Llano (8-11, 15-19 h)': [8, 9, 10, 11, 15, 16, 17, 18, 19],
    'Punta (12-14, 20-23 h)': [12, 13, 14, 20, 21, 22, 23],
}

# Perfiles eólicos ilustrativos (factor de capacidad horario). Son una HIPÓTESIS:
# el enunciado no da datos de viento; sustitúyanse por datos reales si se dispone de ellos.
PERFILES_EOLICOS = {
    'Más viento de noche (FC medio 36 %)': [0.48, 0.50, 0.50, 0.49, 0.47, 0.45, 0.42, 0.37, 0.32, 0.28, 0.25, 0.22,
                                             0.20, 0.20, 0.21, 0.23, 0.26, 0.29, 0.33, 0.37, 0.40, 0.43, 0.45, 0.47],
    'Constante 35 %': [0.35] * 24,
    'Día sin viento (FC medio 10 %)': [0.12, 0.12, 0.11, 0.10, 0.10, 0.09, 0.08, 0.08, 0.08, 0.08, 0.09, 0.09,
                                       0.10, 0.10, 0.10, 0.11, 0.11, 0.11, 0.12, 0.12, 0.12, 0.12, 0.12, 0.12],
    'Día de mucho viento (FC medio 62 %)': [0.70, 0.72, 0.72, 0.70, 0.68, 0.66, 0.64, 0.62, 0.60, 0.58, 0.55, 0.52,
                                            0.50, 0.50, 0.52, 0.55, 0.58, 0.60, 0.62, 0.64, 0.66, 0.68, 0.70, 0.70],
}


def precios_por_tramo(valle, llano, punta):
    p = [0.0] * 24
    for nombre, horas in TRAMOS.items():
        val = valle if nombre.startswith('Valle') else llano if nombre.startswith('Llano') else punta
        for h in horas:
            p[h] = float(val)
    return p


def indicadores(d, r):
    gen = r['gen']
    energia = gen.clip(lower=0).sum()
    co2 = 0.0
    for c, e in energia.items():
        if c in d['EMISION']:
            co2 += e * d['EMISION'][c]
    servida = r['demanda'].sum()
    lin_sat = (r['uso_lineas'] >= 0.995).sum().sort_values(ascending=False) if len(r['uso_lineas'].columns) else pd.Series(dtype=float)
    k = dict(
        coste=r['costes']['total'] - r['costes']['ens'] - r['costes']['co2'] - r['costes']['peso_co2'],
        coste_co2=r['costes']['co2'],
        coste_ens=r['costes']['ens'],
        fijo=r['costes']['fijo'], variable=r['costes']['variable'],
        arranque=r['costes']['arranque'], intercambio=r['costes']['intercambio'],
        co2_t=co2, co2_g_kwh=co2 / servida * 1000 if servida else 0.0,
        ens_mwh=float(r['ens'].sum().sum()) if len(r['ens'].columns) else 0.0,
        deficit_reserva_max=float(r['deficit_reserva'].max()),
        horas_deficit_reserva=int((r['deficit_reserva'] > 0.5).sum()),
        bombeo_mwh=float(r['bombeo'].sum().sum()),
        arranques=int(r['arranques'].sum().sum()),
        holgura_reserva=float((r['reserva'] - r['reserva_req']).min()),
        compra_mwh=float(sum(gen[c].sum() for c in gen.columns if c.startswith('Compra'))),
        venta_mwh=float(-sum(gen[c].sum() for c in gen.columns if c.startswith('Venta'))),
        horas_marcha=r['estado'].sum().to_dict(),
        energia=energia.to_dict(),
        lineas_saturadas={l: int(h) for l, h in lin_sat.items() if h > 0},
    )
    return k


def resolver_escenario(d, tiempo=120):
    m = construir_modelo(d)
    info = resolver(m, tiempo=tiempo)
    if info['coste'] is None:
        return dict(info=info, r=None, k=None)
    r = resultados(m, d)
    return dict(info=info, r=r, k=indicadores(d, r))


def _fmt(x, dec=0):
    s = f'{x:,.{dec}f}'
    return s.replace(',', 'X').replace('.', ',').replace('X', '.')


def interpretar(d, r, k, kb=None):
    """Frases cortas para un decisor que no programa."""
    t = []
    if kb is not None:
        dif = k['coste'] - kb['coste']
        signo = 'más' if dif > 0 else 'menos'
        t.append(f"El día cuesta **{_fmt(k['coste'])} €**, {_fmt(abs(dif))} € {signo} que el caso base "
                 f"({_fmt(100 * dif / kb['coste'], 1)} %)."
                 + (" Ojo: no es comparable, porque hay demanda sin atender." if k['ens_mwh'] > 0.5 else ''))
    else:
        t.append(f"El día cuesta **{_fmt(k['coste'])} €**.")
    if k['ens_mwh'] > 0.5:
        nodos = r['ens'].sum()
        nodos = ', '.join(f'nodo {n} ({_fmt(v)} MWh)' for n, v in nodos.items() if v > 0.5)
        t.append(f"⚠️ **No se puede atender toda la demanda**: faltan {_fmt(k['ens_mwh'])} MWh ({nodos}). "
                 f"El escenario no es viable sin cortes de suministro.")
    if k['horas_deficit_reserva'] > 0:
        t.append(f"⚠️ **La reserva del {_fmt(100 * d['RESERVA'])} % no se cumple** en {k['horas_deficit_reserva']} h "
                 f"(faltan hasta {_fmt(k['deficit_reserva_max'])} MW). El sistema no aguantaría una subida de demanda.")
    hm = k['horas_marcha']
    base = [g for g, h in hm.items() if h == 24]
    punta = [g for g, h in hm.items() if 0 < h < 24]
    paradas = [g for g, h in hm.items() if h == 0]
    if base:
        t.append(f"Centrales de base (24 h en marcha): {', '.join(base)}.")
    if punta:
        t.append('Centrales que se encienden solo parte del día: '
                 + ', '.join(f'{g} ({h} h)' for g, h in hm.items() if 0 < h < 24) + '.')
    if paradas:
        t.append(f"No se usan: {', '.join(paradas)}.")
    if k['lineas_saturadas']:
        top = list(k['lineas_saturadas'].items())[:4]
        t.append('Líneas que trabajan al 100 % más horas: '
                 + ', '.join(f'{l} ({h} h)' for l, h in top) + '. Son los cuellos de botella de la red.')
    if k['horas_deficit_reserva'] > 0:
        pass
    elif k['holgura_reserva'] < 1:
        t.append('La reserva del 15 % está **justa** en al menos una hora: condiciona la solución.')
    else:
        t.append(f"La reserva se cumple con holgura (mínimo {_fmt(k['holgura_reserva'])} MW de margen).")
    if k['bombeo_mwh'] > 1:
        t.append(f"Se bombean {_fmt(k['bombeo_mwh'])} MWh para reponer el agua turbinada.")
    if k['compra_mwh'] > 1 or k['venta_mwh'] > 1:
        t.append(f"Intercambio exterior: se compran {_fmt(k['compra_mwh'])} MWh y se venden {_fmt(k['venta_mwh'])} MWh.")
    t.append(f"Emisiones estimadas: {_fmt(k['co2_t'])} t CO₂-eq ({_fmt(k['co2_g_kwh'])} g/kWh)"
             + (f", {_fmt(k['co2_t'] - kb['co2_t'])} t respecto al caso base." if kb else '.'))
    return t


# ---------------------------------------------------------------------------
# Análisis de sensibilidad: un parámetro, varios valores
# ---------------------------------------------------------------------------
PARAMETROS_BARRIDO = {
    'Precio de compra exterior, todas las horas (€/MWh)': 'precio_compra',
    'Precio de venta exterior, todas las horas (€/MWh)': 'precio_venta',
    'Coste horario al mínimo de una central (×)': 'cmin',
    'Coste extra por MWh de una central (×)': 'cextra',
    'Coste de arranque de una central (×)': 'carr',
    'Potencia máxima de una central (×)': 'pmax',
    'Capacidad de una línea (MW)': 'cap_linea',
    'Nivel inicial del depósito (m)': 'h0',
    'Reserva exigida (%)': 'reserva',
    'Potencia eólica instalada en lugar de la nuclear (MW)': 'p_eolica',
    'Precio del CO₂ dentro del coste (€/t)': 'precio_co2',
    'Tope de emisiones diarias (t CO₂) — frontera de Pareto': 'co2_max',
}


def aplicar(d, clave, valor, objeto=None):
    d = copy.deepcopy(d)
    if clave == 'precio_compra':
        d['INTERCAMBIO'] = True
        d['PRECIO_COMPRA'] = [float(valor)] * 24
    elif clave == 'precio_venta':
        d['INTERCAMBIO'] = True
        d['PRECIO_VENTA'] = [float(valor)] * 24
    elif clave in ('cmin', 'cextra', 'carr', 'pmax'):
        tabla = {'cmin': 'CMIN', 'cextra': 'CEXTRA', 'carr': 'CARR', 'pmax': 'PMAX'}[clave]
        if objeto in d[tabla]:
            d[tabla][objeto] = d[tabla][objeto] * float(valor)
            if clave == 'pmax':
                d['PMIN'][objeto] = min(d['PMIN'][objeto], d['PMAX'][objeto])
    elif clave == 'cap_linea':
        d['CAP_LINEA'][objeto] = float(valor)
    elif clave == 'h0':
        d['H0'] = float(valor)
    elif clave == 'reserva':
        d['RESERVA'] = float(valor) / 100
    elif clave == 'precio_co2':
        d['PRECIO_CO2'] = float(valor)
    elif clave == 'co2_max':
        d['CO2_MAX'] = float(valor)
    elif clave == 'p_eolica':
        d['EOLICA'] = True
        d['P_EOLICA'] = float(valor)
        if sum(d['PERFIL_EOLICO']) == 0:
            d['PERFIL_EOLICO'] = list(PERFILES_EOLICOS.values())[0]
    return d


def barrido(d, clave, valores, objeto=None, progreso=None):
    filas = []
    for i, v in enumerate(valores):
        dd = aplicar(d, clave, v, objeto)
        s = resolver_escenario(dd)
        fila = {'valor': v, 'estado': s['info']['estado']}
        if s['k'] is not None:
            k = s['k']
            fila.update({'coste (€)': k['coste'], 'ENS (MWh)': k['ens_mwh'],
                         'déficit reserva máx (MW)': k['deficit_reserva_max'], 'CO2 (t)': k['co2_t'],
                         'compra (MWh)': k['compra_mwh'], 'venta (MWh)': k['venta_mwh'],
                         'arranques': k['arranques'], 'bombeo (MWh)': k['bombeo_mwh']})
            for g, h in k['horas_marcha'].items():
                fila[f'horas {g}'] = h
        filas.append(fila)
        if progreso:
            progreso((i + 1) / len(valores))
    return pd.DataFrame(filas)


def a_excel(d, r, k):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf) as xw:
        pd.Series({'Coste total (€)': k['coste'], 'Coste fijo (€)': k['fijo'], 'Coste variable (€)': k['variable'],
                   'Arranques (€)': k['arranque'], 'Intercambio (€)': k['intercambio'],
                   'Energía no servida (MWh)': k['ens_mwh'], 'CO2 (t)': k['co2_t'],
                   'Bombeo (MWh)': k['bombeo_mwh']}).to_frame('valor').to_excel(xw, sheet_name='Resumen')
        r['gen'].round(1).to_excel(xw, sheet_name='Generacion_MW')
        r['bombeo'].round(1).to_excel(xw, sheet_name='Bombeo_MW')
        r['estado'].to_excel(xw, sheet_name='Marcha')
        r['nivel'].round(3).to_excel(xw, sheet_name='Nivel_deposito_m')
        if len(r['flujos'].columns):
            r['flujos'].round(1).to_excel(xw, sheet_name='Flujos_MW')
            (r['uso_lineas'] * 100).round(1).to_excel(xw, sheet_name='Uso_lineas_%')
        pd.DataFrame({'Demanda': r['demanda'], 'Reserva disponible': r['reserva'],
                      'Reserva exigida': r['reserva_req']}).round(1).to_excel(xw, sheet_name='Reserva')
        if len(r['ens'].columns):
            r['ens'].round(1).to_excel(xw, sheet_name='ENS_MW')
        pd.Series({k2: str(v) for k2, v in d.items()}).to_frame('valor').to_excel(xw, sheet_name='Escenario')
    return buf.getvalue()
