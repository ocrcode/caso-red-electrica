"""
guia.py — Guía de uso que se muestra en la pestaña «Guía de uso» de la herramienta (app.py).
Está en un archivo aparte para poder editar el texto sin tocar la lógica de la interfaz.
"""
import streamlit as st

RESUMEN = ('**¿Primera vez?** Despliegue la **📖 Guía de uso** arriba de la página: explica en 2 minutos cómo '
           'definir un escenario, resolverlo y leer los resultados.')


def mostrar():
    st.markdown(
        'Esta herramienta calcula la **programación de mínimo coste de un día tipo**: qué centrales '
        'encender cada hora, cuánto debe producir cada una y cómo circula la energía por la red, '
        'cumpliendo la demanda, la reserva del 15 %, los límites de las líneas y los del depósito. '
        'No hace falta saber programar: todo se maneja desde la barra lateral y las pestañas.')

    st.markdown('### Uso en 4 pasos')
    c = st.columns(4)
    c[0].markdown('**1. Nombre**\n\nEscriba un nombre para el escenario en la barra lateral '
                  '(p. ej. «Sin línea A4»).')
    c[1].markdown('**2. Cambios**\n\nAbra los apartados de la barra lateral y cambie sólo lo que '
                  'quiera estudiar. Lo que no toque queda como en el caso base.')
    c[2].markdown('**3. Resolver**\n\nPulse **▶ Resolver escenario**. Tarda menos de un segundo '
                  '(algo más con la reserva por la red o la curva no convexa).')
    c[3].markdown('**4. Leer**\n\nRevise las pestañas de resultados. Guarde el escenario para '
                  'compararlo con otros.')
    st.info('Al abrir la herramienta se muestra el **caso base** (613.800 €/día). Los resultados de '
            'cada escenario se comparan siempre con él: las flechas de la pestaña «Resumen» indican '
            'la diferencia.')

    st.markdown('### Qué se puede cambiar (barra lateral)')
    st.markdown(
        '| Apartado | Para qué sirve | Ejemplo de pregunta |\n'
        '| --- | --- | --- |\n'
        '| **Hipótesis de modelado** | Cambiar las hipótesis H1–H5 de la memoria: lectura de la curva '
        'nuclear, red sí/no, % y forma de la reserva, depósito, nivel inicial y final, bombeo, día cíclico | '
        '¿Cuánto cambia el coste si el depósito empieza a 15 m? |\n'
        '| **Intercambio con redes vecinas** | Permitir comprar o vender energía en los nodos 1 y 5, con '
        'precios de valle, llano y punta | ¿Hasta qué precio compensa comprar fuera? (análisis 1) |\n'
        '| **Centrales** | Marcar centrales averiadas y editar mínimos, máximos y costes en la tabla '
        '(doble clic en una celda) | ¿Qué pasa si se para la nuclear? (análisis 2 y 3) |\n'
        '| **Red eléctrica** | Cortar líneas o cambiar su capacidad | ¿Cuánto se ahorra ampliando A4? '
        '(análisis 4) |\n'
        '| **Parque eólico** | Sustituir la nuclear por eólica: potencia, perfil de viento y costes | '
        '¿Cuántos MW eólicos hacen falta? (análisis 5) |\n'
        '| **Emisiones** | Factores de emisión de A, C y F (gas 0,49; carbón 0,82 t/MWh) | ¿Y si A fuera '
        'de carbón? |\n'
        '| **Permitir cortes de suministro** | Si un escenario es imposible, en vez de no dar solución '
        'indica cuánta demanda y reserva faltan (penalizadas a 10.000 €/MWh) | Déjela marcada al estudiar '
        'averías |')

    st.markdown('### Cómo leer los resultados (pestañas)')
    st.markdown(
        '- **Resumen**: coste del día, demanda no servida, CO₂, arranques y margen de reserva, con la '
        'diferencia frente al caso base. Debajo, frases que explican la solución en lenguaje llano y el '
        'desglose del coste. El botón **💾 Guardar** lo añade a la comparación.\n'
        '- **Despacho**: producción de cada central hora a hora (barras apiladas), bombeo en negativo y la '
        'línea de demanda. Las tablas indican horas en marcha y energía de cada central.\n'
        '- **Depósito y reserva**: nivel del agua (debe estar entre 10 y 20 m) y reserva disponible frente '
        'a la exigida.\n'
        '- **Red**: carga de cada línea por hora; los puntos marcan líneas al 100 %, que son las que '
        'limitan la solución.\n'
        '- **Comparar escenarios**: tabla y gráfico con todos los escenarios guardados.\n'
        '- **Sensibilidad**: repite el cálculo variando **un** parámetro entre dos valores y dibuja cómo '
        'cambia el resultado (ver abajo).\n'
        '- **Datos**: tablas completas y descarga de todos los resultados en Excel.')

    st.markdown('### Análisis de sensibilidad paso a paso')
    st.markdown(
        '1. Defina primero en la barra lateral el escenario de partida (si no cambia nada, es el caso base).\n'
        '2. En la pestaña **Sensibilidad** elija el **parámetro** y, si se pide, la central o la línea.\n'
        '3. Indique **desde**, **hasta** y el **número de puntos** (cada punto es una resolución: 10–15 '
        'puntos tardan unos segundos).\n'
        '4. Elija **qué representar** (coste, demanda no servida, CO₂, compra, venta, arranques o bombeo) '
        'y pulse **▶ Lanzar análisis de sensibilidad**.\n'
        '5. Descargue la tabla en CSV si quiere llevarla a la memoria o a Excel.\n\n'
        'En los parámetros marcados con **(×)** el valor es un multiplicador: 0,5 = la mitad, 1 = igual que '
        'el caso base, 1,5 = un 50 % más. La **frontera de Pareto** coste–CO₂ se obtiene con el parámetro '
        '«Tope de emisiones diarias».')

    st.markdown('### Recetas rápidas')
    rec = st.tabs(['Avería de una central', 'Ampliar una línea', 'Comprar fuera', 'Eólica en lugar de nuclear', 'Reducir emisiones'])  # pestañas: Streamlit no permite expanders anidados
    with rec[0]:
        st.markdown('**¿Qué pasa si se avería una central?**')
        st.markdown('Barra lateral → **Centrales** → «Centrales paradas» → elija la central. Deje marcada '
                    '«Permitir cortes de suministro» y pulse Resolver. En «Resumen», la demanda no servida '
                    'indica cuánto no se puede atender.')
    with rec[1]:
        st.markdown('**¿Cuánto vale ampliar una línea?**')
        st.markdown('Pestaña **Sensibilidad** → parámetro «Capacidad de una línea» → elija la línea → por '
                    'ejemplo de 600 a 900 MW con 7 puntos → represente el coste. La pendiente es el ahorro '
                    'por MW ampliado.')
    with rec[2]:
        st.markdown('**¿Compensa comprar energía a las redes vecinas?**')
        st.markdown('Barra lateral → **Intercambio** → marque «Permitir compra/venta» y ponga los precios. '
                    'Para ver el umbral de precio, use en **Sensibilidad** «Precio de compra exterior» '
                    '(por ejemplo de 0 a 30 €/MWh).')
    with rec[3]:
        st.markdown('**¿Puede la eólica sustituir a la nuclear?**')
        st.markdown('Barra lateral → **Parque eólico** → marque la sustitución, elija potencia y perfil de '
                    'viento → Resolver. Pruebe el perfil «Día sin viento» para ver el peor caso, y en '
                    '**Sensibilidad** varíe la potencia eólica de 0 a 5.000 MW.')
    with rec[4]:
        st.markdown('**¿Cuánto cuesta reducir las emisiones?**')
        st.markdown('Pestaña **Sensibilidad** → «Tope de emisiones diarias» (por ejemplo de 25.000 a '
                    '29.000 t) → represente el coste: es la frontera de Pareto. O bien «Precio del CO₂» para '
                    'ver qué precio basta para que el despacho reduzca emisiones por sí solo.')

    st.markdown('### Avisos y problemas frecuentes')
    st.markdown(
        '- **«El escenario no tiene solución»**: los cambios hacen imposible cubrir la demanda o la reserva. '
        'Marque «Permitir cortes de suministro» y vuelva a resolver para ver dónde falla.\n'
        '- **Los cambios no se aplican**: hay que pulsar **▶ Resolver escenario** después de cada cambio.\n'
        '- **Volver al caso base**: recargue la página del navegador (F5).\n'
        '- **La herramienta no responde**: compruebe que sigue abierta la ventana negra de '
        '`EJECUTAR_HERRAMIENTA.bat`; si la cierra, la herramienta se detiene.\n'
        '- **Venta más cara que compra**: si algún precio de venta supera a uno de compra, el modelo podría '
        'comprar y vender a la vez; la barra lateral lo avisa.\n'
        '- La formulación completa del modelo está en `MODELO.md` y en el capítulo 4 de la memoria.')
