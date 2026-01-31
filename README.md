> **Este proyecto se distribuye bajo la licencia Mozilla Public License 2.0 (MPL 2.0).**  
> Asegúrate de leer y comprender la licencia antes de usar o modificar el código.

---

Ya que se trata de un proyecto colaborativo, te invitamos a compartir cualquier sugerencia de mejora asociada a este sistema, todos merecen acceso al conocimiento.

---

# Engine Factory

Herramienta experimental para **desarrollar programas en C** mediante un enfoque modular, determinista y de bajo overhead.

El proyecto está orientado a **composición de sistemas** más que a frameworks monolíticos, permitiendo construir ejecutables y herramientas (simulaciones, editores, motores, utilidades) a partir de módulos atómicos que operan sobre una estructura de datos común.

---

## Objetivo

Explorar y validar un modelo de desarrollo en C que permita:

- Ensamblar programas a partir de **módulos independientes**
- Minimizar overhead en CPU y GPU
- Mantener **determinismo** y control explícito del flujo
- Facilitar herramientas auxiliares (ej. editores) que **no ejecutan lógica**, solo construyen datos
- Permitir escalabilidad hacia simulaciones, motores y procesamiento masivo

---

## Qué es

- Una **herramienta de desarrollo en C**
- Un sistema de composición de módulos
- Un entorno experimental orientado a rendimiento y control
- Una base para:
  - simulaciones
  - motores de juego
  - herramientas offline
  - editores de escenas / datos
  - procesamiento por chunks

---

## Qué NO es

- Un engine completo
- Un framework de alto nivel
- Una librería estable o production-ready
- Un reemplazo de toolchains existentes

Este proyecto **prioriza investigación y exploración**.

---

## Principios de diseño

- **C puro** como lenguaje base
- Datos explícitos > abstracciones implícitas
- Modularidad sin acoplamiento oculto
- SoA cuando aporta beneficios reales
- Multithreading controlado y determinista
- GPU usada como acelerador, no como caja negra

---

## Estado del proyecto

🧪 Experimental / Research project

El diseño, las APIs y la estructura pueden cambiar sin previo aviso.

---

## Licencia

Este proyecto se distribuye bajo la licencia **Mozilla Public License 2.0 (MPL 2.0)**.

- Puedes usarlo libremente
- Puedes integrarlo en proyectos cerrados
- Las modificaciones a archivos existentes bajo MPL deben permanecer abiertas

Ver el archivo `LICENSE` para más detalles.

---

## Público objetivo

Principalmente:

- Personas interesadas en motores, simulaciones o sistemas
- Desarrolladores que valoran control y rendimiento
- Investigación, prototipado y exploración técnica

Pero cualquiera puede usarlo si gusta.

---

## Nota final

Este repositorio se publica con fines de **transparencia y colaboración**, no como producto final.
El enfoque es aprender, medir, iterar y compartir resultados.

