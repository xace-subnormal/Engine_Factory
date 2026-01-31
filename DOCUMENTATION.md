# Engine Factory — Documentación Técnica

Bienvenido a **Engine Factory**, una **herramienta experimental para construir programas en C** mediante composición de módulos, generación de código y un enfoque explícito y determinista orientado a datos.

Engine Factory **no es un motor cerrado**, sino un entorno de exploración técnica que permite ensamblar ejecutables (simulaciones, herramientas, editores, prototipos, motores experimentales) a partir de módulos atómicos que operan sobre una estructura de datos común.

---

## Índice

1. [Conceptos Básicos](#1-conceptos-básicos)
   * [Archivo `.spec`](#archivo-spec)
   * [Generación de código](#generación-de-código)
2. [Uso Avanzado](#2-uso-avanzado)
   * [Backends y ejecución](#backends-y-ejecución)
   * [Diseño orientado a datos (SoA)](#diseño-orientado-a-datos-soa)
   * [Tipado Estricto y Directivas](#tipado-estricto-y-directivas)
   * [Ejecución por fases y rangos](#ejecución-por-fases-y-rangos)
3. [Sistema de Reglas (Experimental)](#3-sistema-de-reglas-experimental)
   * [Sintaxis de Archivos .rule](#sintaxis-de-archivos-rule)
4. [Guía para Desarrolladores](#4-guía-para-desarrolladores)

---

## 1. Conceptos Básicos

Engine Factory utiliza archivos de especificación (`.spec`) como **fuente declarativa** para describir:

* datos
* entidades
* fases de ejecución
* módulos que deben ensamblarse

El *builder* traduce esta descripción en **código C explícito**, sin runtimes ocultos ni reflexión dinámica.

### Archivo `.spec`

Un archivo `.spec` define **datos y estructura**, no “gameplay” en sentido tradicional.

```ini
# Entidad única (estado global explícito)
UNIQUE World:
 @@gravity float = 9.8f
 @@game_over bool = false

# Entidad genérica (instancias múltiples)
GENERIC Player count=1:
 @@position_x float = 0.0f
 @@health int = 100

# Fases de ejecución
SYSTEM PlayerControl PHASE LOOP
SYSTEM Physics PHASE LOOP
```

Nota:
El archivo `.spec` **no es un lenguaje de scripting**, es una descripción estructural que permite generar código C determinista.

---

### Generación de código

```bash
python3 builder.py specs/mi_programa.spec
```

Esto genera un archivo `main.c` (y código auxiliar si corresponde).

La compilación **no es impuesta por el sistema**:

```bash
gcc main.c -O2 -march=native -lpthread -lm
```

Cada proyecto puede decidir:

* flags
* backend gráfico
* uso o no de GPU
* modo headless

---

## 2. Uso Avanzado

### Backends y ejecución

Engine Factory **no fuerza un backend gráfico**.
Algunos módulos pueden inyectar helpers opcionales.

```ini
BACKEND MANUAL
```
Significa que no se inyecta ningún loop de render, además, otros backends pueden existir como **módulos intercambiables**, no como dependencia central.

Esto permite:

* herramientas offline
* simulaciones
* editores
* servidores
* ejecutables sin ventana

---

### Diseño orientado a datos (SoA)

Engine Factory permite describir **estructuras separables** que el builder puede expandir en SoA cuando es conveniente.

```ini
SOA Vector3 float x y z

GENERIC Cube count=100000:
 @@position Vector3 = {0,0,0}
```

Esto genera arrays planos (`position_x[]`, `position_y[]`, `position_z[]`) sin imponer un ECS rígido.

SoA **no es obligatorio**, se usa cuando aporta beneficios reales.

---

### Tipado Estricto y Directivas

#### `strict`
Si necesitas que una estructura se mantenga contigua en memoria (AoS) en lugar de desenrollarse en arrays (SoA), usa el modificador `strict`. Esto es vital para interactuar con librerías externas que esperan punteros a structs completos (ej. APIs de física o renderizado).

```ini
SOA Vector3 float x y z

GENERIC Player count=10:
 strict @@position Vector3 = {0,0,0} 
 # Genera: Vector3 position[10]; (No position_x[], position_y[]...)
```

#### Otras Directivas
*   `CONFIG MAX_THREADS <int>`: Define el número de hilos para el pool de trabajadores.
*   `[TYPE NuevoTipo TipoBase]`: Crea alias de tipos (ej. `[TYPE mi_entero int32]`).
*   `SYSTEM <Nombre> PRIORITY <int>`: Establece el orden de ejecución (menor = antes).
*   `SYSTEM <Nombre> MODE [SINGLE|PARALLEL]`: Define si el sistema se ejecuta en un solo hilo o distribuido.

---

### Ejecución por fases y rangos

Los sistemas se organizan por **fases explícitas** (`START`, `LOOP`, `END`) y pueden operar sobre rangos de datos.

```ini
SYSTEM Physics PHASE LOOP
SYSTEM Collision PHASE LOOP
```

El paralelismo:

* es **explícito**
* se basa en rangos contiguos
* evita scheduling dinámico no determinista

---

## 3. Sistema de Reglas (Experimental)

Engine Factory incluye un **transpilador experimental** (`script_builder.py`) que permite expresar lógica declarativa en archivos `.rule` y convertirla automáticamente en módulos C optimizados.

Este sistema:

* está en investigación
* no es estable
* puede cambiar o desaparecer

### Flujo

1. Crear archivo `.rule` en la carpeta `rules/`.
2. Ejecutar el transpilador: `python3 script_builder.py`.
3. Esto genera un archivo C en `modules/` con el prefijo `sys_` (ej. `sys_Combat.c`).
4. Incluir el nuevo sistema en el `.spec` (ej. `SYSTEM sys_Combat PHASE LOOP`).

### Sintaxis de Archivos .rule

El lenguaje es declarativo y se centra en condiciones y acciones sobre una entidad.

#### Cabecera
```yaml
MODULE_ENTITY: Player
REQ: Player.health as hp WRITE
REQ: Player.pos_x as px READ
REQ: World.damage_area as dmg READ
```

Definiciones:

*   `MODULE_ENTITY`: La entidad sobre la que iterará el sistema.
*   `REQ`: Inyección de variables.
*   Formato: `Entidad.Propiedad as Alias [ARRAY|SINGLE] [READ|WRITE|READ_WRITE]`
*   Por defecto: `READ`. Si se omite `ARRAY/SINGLE`, se infiere según si la entidad coincide con `MODULE_ENTITY`.

#### Reglas
Un archivo puede contener múltiples bloques `RULE`.

```yaml
RULE: CheckDamage
CONDITIONS:
    px > 100
    px < 200
    hp > 0
ACTIONS:
    SET hp = hp - dmg
    EMIT PLAYER_HIT px hp
```

Definiciones:

*   `CONDITIONS`: Lista de expresiones booleanas. Se unen implícitamente con `AND`.
*   Se pueden usar prefijos opcionales: `WHEN`, `AND`, `OR`, `NOT` (aunque la lógica actual las trata mayormente como AND).
*   `ACTIONS`: Comandos a ejecutar si las condiciones son verdaderas.
*   `SET <Alias> = <Expresion>`: Asignación de valores.
*   `EMIT <Evento> <Arg1> <Arg2>...`: Emite un evento personalizado (macros C).
*   `DESTROY`: Marca la entidad actual como inactiva.
*   Cualquier otra línea se transpile tal cual a C (ej. llamadas a funciones).

El resultado final **siempre es código C explícito**, sin intérpretes.

---

## 4. Guía para Desarrolladores

### Arquitectura general

Engine Factory separa estrictamente:

* **infraestructura** (builder, generación)
* **datos**
* **módulos**

No hay:

* herencia
* reflexión
* entidades dinámicas ocultas

---

### Módulos C y dependencias

Los módulos declaran dependencias mediante comentarios analizados estáticamente.

```c
// REQ: Player.health as hp
// REQ: World.gravity as g

void system_MiModulo(int* hp, float* g) {
    *hp -= (int)(*g);
}
```

El builder:

* conecta punteros
* genera llamadas
* mantiene el flujo explícito

No hay inyección en runtime.

---

### Estructura de directorios (sujeta a cambios)

```
/modules     -> módulos C
/specs       -> definición estructural
/rules       -> reglas experimentales (.rule)
/generated   -> salida intermedia (opcional)
```

---

## Nota final

Esta documentación describe el **estado conceptual actual**, no una API estable.

Engine Factory es:

* una base de exploración
* una herramienta para experimentar con composición en C
* un sistema para aprender, medir y descartar ideas
