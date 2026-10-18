# Caso Red Eléctrica · MCOI (UPV)

Código del trabajo en equipo de la asignatura *Métodos Cuantitativos para la Organización Industrial*: modelo de *unit commitment* con red, bombeo y reserva, implementado en Python con **Pyomo** y resuelto con **HiGHS**.

## Archivos

| Archivo | Qué es |
| --- | --- |
| `modelo_uc.py` | Script principal: datos, modelo, resolución y resultados |
| `requirements.txt` | Paquetes de Python necesarios |
| `.gitignore` | Archivos que Git no debe subir (cachés, entornos virtuales, logs del solver) |

## Cómo ejecutarlo

En el ordenador (Python 3.10 o superior):

```bash
pip install -r requirements.txt
python modelo_uc.py
```

Sin instalar nada: en la página del repositorio, **Code → Codespaces → Create codespace on main** abre un VS Code en el navegador con Python ya listo; allí se ejecutan los dos comandos anteriores en la terminal.

## Cómo trabajamos

Así cada cambio queda registrado con su autor, su fecha y su motivo.

1. **Una rama por tarea.** No se edita `main` directamente: se crea una rama (`modelo-bombeo`, `analisis-eolica`…). En la web, al editar un archivo y pulsar *Commit changes*, elegid *Create a new branch*.
2. **Commits pequeños y con mensaje claro**, que digan qué cambia: «Añade restricción de reserva del 15 %», no «cambios».
3. **Pull request para unir a `main`.** Otro miembro del equipo lo revisa y lo aprueba antes de fusionarlo.
4. **Decisiones de modelado en el código o en el PR.** Si se adopta una hipótesis (por ejemplo, cómo se lee el eje «€» de la Figura 1), se deja escrita en un comentario o en la descripción del PR para poder citarla en la memoria.

Para editar rápido desde el navegador: abrid el archivo en GitHub y pulsad el lápiz, o pulsad la tecla `.` en la página del repositorio para abrir el editor web.
