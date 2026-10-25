"""
app.py — Herramienta de apoyo a la decisión (Streamlit) del Caso Red Eléctrica.

Ejecutar:   streamlit run app.py
Requiere:   pip install -r requirements.txt   (pyomo, highspy, streamlit, pandas, matplotlib, openpyxl)

El decisor define un escenario en la barra lateral, pulsa «Resolver» y lee los resultados en
las pestañas. No necesita programar: todo el cálculo está en escenarios.py / modelo.py.
"""
import copy
import numpy as np
import pandas as pd
import streamlit as st

from datos import escenario_base
import escenarios as esc
import graficos as gr

st.set_page_config(page_title='Red Eléctrica · Programación de la generación', page_icon='⚡', layout='wide')


# ---------------------------------------------------------------------------
# Caso base (se calcula una vez y se reutiliza para comparar)
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner='Resolviendo el caso base…')
def caso_base():
    d = escenario_base()
    d['ENS'] = True
    s = esc.resolver_escenario(d)
    return d, s['r'], s['k']


def eur(x):
    return esc._fmt(x) + ' €'


d_base, r_base, k_base = caso_base()

if 'comparados' not in st.session_state:
    st.session_state['comparados'] = [dict(Escenario='Caso base', **{
        'Coste (€)': k_base['coste'], 'No servida (MWh)': k_base['ens_mwh'], 'CO₂ (t)': k_base['co2_t'],
        'Arranques': k_base['arranques'], 'Bombeo (MWh)': k_base['bombeo_mwh'],
        'Compra (MWh)': k_base['compra_mwh'], 'Venta (MWh)': k_base['venta_mwh']})]

# ---------------------------------------------------------------------------
# BARRA LATERAL: definición del escenario
# ---------------------------------------------------------------------------
sb = st.sidebar
sb.title('⚡ Escenario')
nombre = sb.text_input('Nombre del escenario', 'Mi escenario')
d = escenario_base()

with sb.expander('Hipótesis de modelado', expanded=False):
    lect = st.selectbox('Lectura de la curva de la nuclear',
                        ['marginal', 'medio', 'total_k'],
                        format_func=lambda x: {'marginal': 'Coste marginal (€/MWh) — base',
                                               'medio': 'Coste medio (€/MWh)',
                                               'total_k': 'Coste total (k€/h) — no convexa'}[x])
    d['LECTURA_CURVA_D'] = lect
    d['RED'] = st.checkbox('Tener en cuenta la red', True)
    d['RESERVA'] = st.slider('Reserva exigida (% de la demanda)', 0, 30, 15) / 100
    d['RESERVA_MODO'] = st.radio('Cómo se comprueba la reserva', ['sistema', 'red'],
                                 format_func=lambda x: 'Todo el sistema' if x == 'sistema' else 'Que llegue por la red',
                                 horizontal=True)
    d['RESERVA_HIDRO_SIN_AGUA'] = st.checkbox(
        'La reserva hidráulica puede bajar de 10 m (enunciado)', True,
        help='Si se desmarca, B y E sólo cuentan como reserva si queda agua en el depósito para turbinar una hora.')
    d['DEPOSITO_COMPARTIDO'] = st.checkbox('Un único depósito para B y E', True)
    d['H0'] = st.slider('Nivel inicial del depósito (m)', 10.0, 20.0, 10.0, 0.5)
    d['CIERRE_DEPOSITO'] = st.selectbox('Nivel al final del día', ['>=', '==', 'libre'],
                                        format_func=lambda x: {'>=': '≥ inicial (base)', '==': '= inicial',
                                                               'libre': 'Libre'}[x])
    if not st.checkbox('Permitir bombeo', True):
        d['PBOMBA'] = {'B': 0.0, 'E': 0.0}
    d['CICLICO'] = st.checkbox('Día tipo cíclico', True,
                               help='Si se desmarca, a las 0:00 solo están encendidas A y D.')

with sb.expander('Intercambio con redes vecinas', expanded=False):
    d['INTERCAMBIO'] = st.checkbox('Permitir compra/venta en los nodos 1 y 5', False)
    cap = st.number_input('Capacidad de cada conexión (MW)', 0, 2000, 500, 50)
    d['CAP_EXT'] = {1: float(cap), 5: float(cap)}
    st.caption('Precios de compra (€/MWh)')
    c1, c2, c3 = st.columns(3)
    pcv = c1.number_input('Valle', 0.0, 500.0, 4.0, 0.5, key='pcv')
    pcl = c2.number_input('Llano', 0.0, 500.0, 6.0, 0.5, key='pcl')
    pcp = c3.number_input('Punta', 0.0, 500.0, 10.0, 0.5, key='pcp')
    st.caption('Precios de venta (€/MWh)')
    c1, c2, c3 = st.columns(3)
    pvv = c1.number_input('Valle', 0.0, 500.0, 0.0, 0.5, key='pvv')
    pvl = c2.number_input('Llano', 0.0, 500.0, 0.0, 0.5, key='pvl')
    pvp = c3.number_input('Punta', 0.0, 500.0, 0.0, 0.5, key='pvp')
    d['PRECIO_COMPRA'] = esc.precios_por_tramo(pcv, pcl, pcp)
    d['PRECIO_VENTA'] = esc.precios_por_tramo(pvv, pvl, pvp)
    if max(d['PRECIO_VENTA']) > min(d['PRECIO_COMPRA']):
        st.warning('Algún precio de venta supera a uno de compra: el modelo podría comprar y vender a la vez.')

with sb.expander('Centrales', expanded=False):
    d['INDISPONIBLES'] = st.multiselect('Centrales paradas (avería o mantenimiento)', ['A', 'B', 'C', 'D', 'E', 'F'])
    tabla = pd.DataFrame({
        'Mínimo (MW)': [d['PMIN'][g] for g in 'ACFD'],
        'Máximo (MW)': [d['PMAX'][g] for g in 'ACFD'],
        'Coste al mínimo (€/h)': [d['CMIN'][g] for g in 'ACFD'],
        'Coste extra (€/MWh)': [d['CEXTRA'].get(g, np.nan) for g in 'ACFD'],
        'Arranque (€)': [d['CARR'][g] for g in 'ACFD']}, index=list('ACFD'))
    st.caption('Térmicas y nuclear (el coste extra de D sale de su curva)')
    tabla = st.data_editor(tabla, key='t_centrales', disabled=False)
    for g in 'ACFD':
        d['PMIN'][g] = float(tabla.loc[g, 'Mínimo (MW)'])
        d['PMAX'][g] = float(tabla.loc[g, 'Máximo (MW)'])
        d['CMIN'][g] = float(tabla.loc[g, 'Coste al mínimo (€/h)'])
        d['CARR'][g] = float(tabla.loc[g, 'Arranque (€)'])
        if g in d['CEXTRA'] and not pd.isna(tabla.loc[g, 'Coste extra (€/MWh)']):
            d['CEXTRA'][g] = float(tabla.loc[g, 'Coste extra (€/MWh)'])
    st.caption('Hidráulicas')
    th = pd.DataFrame({'Potencia (MW)': [d['PH'][g] for g in 'BE'], 'Coste (€/h)': [d['CH'][g] for g in 'BE'],
                       'Arranque (€)': [d['CARR'][g] for g in 'BE']}, index=list('BE'))
    th = st.data_editor(th, key='t_hidro')
    for g in 'BE':
        d['PH'][g] = float(th.loc[g, 'Potencia (MW)'])
        d['CH'][g] = float(th.loc[g, 'Coste (€/h)'])
        d['CARR'][g] = float(th.loc[g, 'Arranque (€)'])

with sb.expander('Red eléctrica', expanded=False):
    d['LINEAS_CORTADAS'] = st.multiselect('Líneas cortadas', list(d['LINEAS'].keys()))
    tl = pd.DataFrame({'Capacidad (MW)': [d['CAP_LINEA'][l] for l in d['LINEAS']]}, index=list(d['LINEAS']))
    tl = st.data_editor(tl, key='t_lineas')
    for l in d['LINEAS']:
        d['CAP_LINEA'][l] = float(tl.loc[l, 'Capacidad (MW)'])

with sb.expander('Parque eólico (sustituye a la nuclear)', expanded=False):
    d['EOLICA'] = st.checkbox('Sustituir la nuclear D por un parque eólico en su nodo', False)
    d['P_EOLICA'] = float(st.number_input('Potencia instalada (MW)', 0, 6000, 2000, 100))
    perfil = st.selectbox('Perfil de viento (hipótesis)', list(esc.PERFILES_EOLICOS))
    d['PERFIL_EOLICO'] = esc.PERFILES_EOLICOS[perfil]
    d['C_EOLICA'] = float(st.number_input('Coste variable (€/MWh)', 0.0, 50.0, 0.0, 0.5))
    d['CMIN_EOLICA'] = float(st.number_input('Coste fijo (€/h)', 0.0, 20000.0, 0.0, 100.0))
    st.caption('La eólica no aporta reserva firme: la reserva del 15 % debe cubrirse con el resto de centrales.')

with sb.expander('Emisiones (t CO₂-eq/MWh)', expanded=False):
    st.caption('El enunciado no dice qué combustible usan A, C y F. '
               'Gas de ciclo combinado ≈ 0,49; carbón ≈ 0,82 (IPCC AR5).')
    for g in ['A', 'C', 'F']:
        d['EMISION'][g] = st.number_input(f'Factor {g}', 0.0, 1.5, d['EMISION'][g], 0.01, key=f'em{g}')

d['ENS'] = sb.checkbox('Permitir cortes de suministro (diagnóstico)', True,
                       help='Si una situación es imposible (p. ej. una central averiada), el modelo indica cuánta '
                            'demanda quedaría sin atender en lugar de no dar solución. Se penaliza a 10.000 €/MWh.')

resolver = sb.button('▶ Resolver escenario', type='primary', use_container_width=True)
if resolver:
    with st.spinner('Optimizando…'):
        s = esc.resolver_escenario(d)
    st.session_state['actual'] = dict(nombre=nombre, d=d, **s)

# ---------------------------------------------------------------------------
# ZONA PRINCIPAL
# ---------------------------------------------------------------------------
st.title('Programación de la generación de un día tipo')
st.caption('Modelo MILP (Pyomo + HiGHS) · Caso Red Eléctrica · MCOI 2026-27')

act = st.session_state.get('actual')
if act is None:
    st.info('Defina un escenario en la barra lateral y pulse **Resolver**. Mientras tanto se muestra el caso base.')
    act = dict(nombre='Caso base', d=d_base, r=r_base, k=k_base, info=dict(estado='optimal'))

if act['k'] is None:
    st.error(f"El escenario no tiene solución (estado: {act['info']['estado']}). "
             'Active «Permitir cortes de suministro» para ver dónde falla.')
    st.stop()

dd, r, k = act['d'], act['r'], act['k']
es_base = act['nombre'] == 'Caso base' and act.get('info', {}).get('solver') is None

t_res, t_desp, t_dep, t_red, t_comp, t_sens, t_datos = st.tabs(
    ['Resumen', 'Despacho', 'Depósito y reserva', 'Red', 'Comparar escenarios', 'Sensibilidad', 'Datos'])

with t_res:
    st.subheader(act['nombre'])
    c = st.columns(5)
    c[0].metric('Coste del día', eur(k['coste']),
                None if es_base else eur(k['coste'] - k_base['coste']), delta_color='inverse')
    c[1].metric('Demanda no servida', esc._fmt(k['ens_mwh']) + ' MWh')
    c[2].metric('Emisiones', esc._fmt(k['co2_t']) + ' t CO₂',
                None if es_base else esc._fmt(k['co2_t'] - k_base['co2_t']) + ' t', delta_color='inverse')
    c[3].metric('Arranques', k['arranques'])
    c[4].metric('Margen mínimo de reserva', esc._fmt(k['holgura_reserva']) + ' MW')
    st.markdown('#### Qué dice la solución')
    for frase in esc.interpretar(dd, r, k, None if es_base else k_base):
        st.markdown('- ' + frase)
    st.markdown('#### Desglose del coste')
    st.dataframe(pd.DataFrame({'€': [k['fijo'], k['variable'], k['arranque'], k['intercambio']]},
                              index=['Coste horario al mínimo', 'Coste por encima del mínimo',
                                     'Arranques', 'Intercambio exterior (compra − venta)']).round(0),
                 use_container_width=True)
    if st.button('💾 Guardar este escenario para compararlo'):
        st.session_state['comparados'].append(dict(Escenario=act['nombre'], **{
            'Coste (€)': k['coste'], 'No servida (MWh)': k['ens_mwh'], 'CO₂ (t)': k['co2_t'],
            'Arranques': k['arranques'], 'Bombeo (MWh)': k['bombeo_mwh'],
            'Compra (MWh)': k['compra_mwh'], 'Venta (MWh)': k['venta_mwh']}))
        st.success('Guardado. Véalo en la pestaña «Comparar escenarios».')

with t_desp:
    st.pyplot(gr.despacho(r, f"Producción por central y hora — {act['nombre']}"))
    st.markdown('**Horas en marcha por central**')
    st.dataframe(pd.DataFrame(k['horas_marcha'], index=['horas']), use_container_width=True)
    st.markdown('**Energía producida (MWh)**')
    st.dataframe(pd.DataFrame(k['energia'], index=['MWh']).round(0), use_container_width=True)

with t_dep:
    st.pyplot(gr.deposito(r, dd))
    st.pyplot(gr.reserva(r))

with t_red:
    if len(r['uso_lineas'].columns):
        st.pyplot(gr.lineas(r))
        sat = pd.Series(k['lineas_saturadas'], name='horas al 100 %')
        if len(sat):
            st.markdown('**Líneas saturadas** (horas al 100 % de su capacidad)')
            st.dataframe(sat.to_frame(), use_container_width=True)
        else:
            st.success('Ninguna línea llega al 100 % de su capacidad.')
    else:
        st.info('Este escenario no tiene en cuenta la red (nudo único).')

with t_comp:
    tabla = pd.DataFrame(st.session_state['comparados']).set_index('Escenario')
    st.dataframe(tabla.round(0), use_container_width=True)
    if len(tabla) > 1:
        st.bar_chart(tabla['Coste (€)'])
    if st.button('Vaciar comparación'):
        st.session_state['comparados'] = st.session_state['comparados'][:1]
        st.rerun()

with t_sens:
    st.markdown('Resuelve el escenario de la barra lateral varias veces cambiando **un** parámetro.')
    etiqueta = st.selectbox('Parámetro', list(esc.PARAMETROS_BARRIDO))
    clave = esc.PARAMETROS_BARRIDO[etiqueta]
    objeto = None
    if clave in ('cmin', 'cextra', 'carr', 'pmax'):
        objeto = st.selectbox('Central', ['A', 'C', 'F', 'D'] if clave != 'cextra' else ['A', 'C', 'F'])
    if clave == 'cap_linea':
        objeto = st.selectbox('Línea', list(dd['LINEAS']))
    defecto = {'precio_compra': (0.0, 12.0, 13), 'precio_venta': (0.0, 12.0, 13), 'cmin': (0.5, 1.5, 11),
               'cextra': (0.5, 1.5, 11), 'carr': (0.0, 3.0, 7), 'pmax': (0.6, 1.2, 7),
               'cap_linea': (0.0, 1000.0, 11), 'h0': (10.0, 20.0, 11), 'reserva': (0.0, 30.0, 7),
               'p_eolica': (0.0, 5000.0, 11), 'precio_co2': (0.0, 100.0, 11),
               'co2_max': (25000.0, 29000.0, 9)}[clave]
    c1, c2, c3 = st.columns(3)
    vmin = c1.number_input('Desde', value=float(defecto[0]))
    vmax = c2.number_input('Hasta', value=float(defecto[1]))
    npts = c3.number_input('Número de puntos', 2, 30, int(defecto[2]))
    columna = st.selectbox('Qué representar', ['coste (€)', 'ENS (MWh)', 'CO2 (t)', 'compra (MWh)',
                                               'venta (MWh)', 'arranques', 'bombeo (MWh)'])
    if st.button('▶ Lanzar análisis de sensibilidad'):
        barra = st.progress(0.0)
        base_sens = copy.deepcopy(dd)
        df = esc.barrido(base_sens, clave, list(np.linspace(vmin, vmax, int(npts))), objeto,
                         progreso=lambda p: barra.progress(p))
        st.session_state['sens'] = (df, etiqueta + (f' · {objeto}' if objeto else ''))
    if 'sens' in st.session_state:
        df, etq = st.session_state['sens']
        if columna in df:
            st.pyplot(gr.barrido(df, etq, columna))
        st.dataframe(df.round(1), use_container_width=True)
        st.download_button('Descargar tabla (CSV)', df.to_csv(index=False).encode('utf-8'),
                           'sensibilidad.csv', 'text/csv')

with t_datos:
    st.markdown('**Producción (MW)**')
    st.dataframe(r['gen'].round(1), use_container_width=True)
    if len(r['flujos'].columns):
        st.markdown('**Flujos por las líneas (MW, positivo en el sentido de su nombre)**')
        st.dataframe(r['flujos'].round(1), use_container_width=True)
    st.download_button('📥 Descargar todos los resultados (Excel)', esc.a_excel(dd, r, k),
                       f"{act['nombre'].replace(' ', '_')}.xlsx",
                       'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
