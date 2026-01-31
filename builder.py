#!/usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


# Engine Factory Builder

import sys
import os
import re
import configparser
from collections import OrderedDict

if len(sys.argv) < 2:
    die("Uso: builder.py <archivo.spec> [archivo.gspec]")

SPEC = sys.argv[1]
GSPEC = sys.argv[2] if len(sys.argv) > 2 else None
OUT = "main.c"
MODS = "modules"

gspec_data = {
    "gcomponent": None,
    "entity": None,
    "visibility": None,
    "transform": None,
    "color": None
}

MAX_THREADS = 8
SOA_TYPES = {}
SELECTED_BACKEND = "raylib"


TYPE_MAP = {
    "int": "int",
    "uint": "unsigned int",
    "int8": "int8_t",
    "uint8": "uint8_t",
    "int16": "int16_t",
    "uint16": "uint16_t",
    "int32": "int32_t",
    "uint32": "uint32_t",
    "int64": "int64_t",
    "uint64": "uint64_t",
    "float": "float",
    "double": "double",
    "bool": "bool",
    "string": "const char*",
}

def die(msg):
    print(f"\033[91m[ERROR]\033[0m {msg}")
    sys.exit(1)

def warn(msg):
    print(f"\033[93m[WARN]\033[0m {msg}")

def parse_gspec(gspec_file, entities_data, gspec_output_data):
    if not gspec_file:
        return

    config = configparser.ConfigParser()
    try:
        config.read(gspec_file)
    except Exception as e:
        die(f"Error al leer el archivo GSPEC '{gspec_file}': {e}")

    if 'gcomponent CubeVisuals' not in config:
        die("GSPEC Error: Sección '[gcomponent CubeVisuals]' no encontrada.")
    gcomp_section = config['gcomponent CubeVisuals']
    gspec_output_data['gcomponent'] = 'CubeVisuals'

    entity_name = gcomp_section.get('entity')
    if not entity_name:
        die("GSPEC Error: 'entity' no especificado en '[gcomponent CubeVisuals]'.")
    if entity_name not in entities_data:
        die(f"GSPEC Error: Entidad '{entity_name}' del GSPEC no definida en el archivo SPEC.")
    if entities_data[entity_name]['kind'] != 'GENERIC':
        die(f"GSPEC Error: La entidad '{entity_name}' debe ser de tipo GENERIC para ser sincronizada con el renderizado instanciado.")
    gspec_output_data['entity'] = entity_name

    if 'visibility' in config:
        vis_section = config['visibility']
        gspec_output_data['visibility'] = {
            'when': vis_section.get('when'),
            'else': vis_section.get('else')
        }
        if not gspec_output_data['visibility']['when']:
            die("GSPEC Error: 'when' no especificado en '[visibility]'.")
        vis_var = gspec_output_data['visibility']['when']
        if vis_var not in entities_data[entity_name]['vars']:
            die(f"GSPEC Error: Variable '{entity_name}.{vis_var}' para 'visibility.when' no declarada en la entidad.")
        if entities_data[entity_name]['vars'][vis_var] != 'bool':
            warn(f"GSPEC Advertencia: La variable '{entity_name}.{vis_var}' para 'visibility.when' no es de tipo booleano.")
        if gspec_output_data['visibility']['else'] not in ['alpha_zero']:
            warn(f"GSPEC Advertencia: 'else' desconocido '{gspec_output_data['visibility']['else']}' en '[visibility]'. Se espera 'alpha_zero'.")

    if 'transform' in config:
        trans_section = config['transform']
        gspec_output_data['transform'] = {
            'update_when': trans_section.get('update_when'),
            'type': trans_section.get('type'),
            'from': trans_section.get('from')
        }
        if not gspec_output_data['transform']['type']:
            die("GSPEC Error: 'type' no especificado en '[transform]'.")
        if not gspec_output_data['transform']['from']:
            die("GSPEC Error: 'from' no especificado en '[transform]'.")
        if gspec_output_data['transform']['type'] not in ['translation']:
            die(f"GSPEC Error: Tipo de transformación desconocido '{gspec_output_data['transform']['type']}'. Se espera 'translation'.")

        if gspec_output_data['transform']['update_when']:
            update_var = gspec_output_data['transform']['update_when']
            if update_var not in entities_data[entity_name]['vars']:
                die(f"GSPEC Error: Variable '{entity_name}.{update_var}' para 'transform.update_when' no declarada en la entidad.")
            if entities_data[entity_name]['vars'][update_var] != 'bool':
                warn(f"GSPEC Advertencia: La variable '{entity_name}.{update_var}' para 'transform.update_when' no es de tipo booleano.")

    if 'color' in config:
        color_section = config['color']
        gspec_output_data['color'] = {
            'type': color_section.get('type'),
            'from': color_section.get('from')
        }
        if not gspec_output_data['color']['type']:
            warn("GSPEC Advertencia: 'type' no especificado en '[color]'. Asumiendo 'hex_to_rgba'.")
            gspec_output_data['color']['type'] = 'hex_to_rgba'
        if not gspec_output_data['color']['from']:
            die("GSPEC Error: 'from' no especificado en '[color]'.")
        if gspec_output_data['color']['type'] not in ['hex_to_rgba']:
            die(f"GSPEC Error: Tipo de color desconocido '{gspec_output_data['color']['type']}'. Se espera 'hex_to_rgba'.")
        
        color_var = gspec_output_data['color']['from']
        if color_var not in entities_data[entity_name]['vars']:
            die(f"GSPEC Error: Variable '{entity_name}.{color_var}' para 'color.from' no declarada en la entidad.")
        if entities_data[entity_name]['vars'][color_var] not in ['int', 'uint', 'uint32']:
            warn(f"GSPEC Advertencia: La variable '{entity_name}.{color_var}' para 'color.from' no es de tipo entero (esperado para hex_to_rgba).")

# PARSER

entities = {}
globals = {
    "PRE_START": [],
    "START": [],
    "LOOP": [],
    "POST_LOOP": [],
    "END": []
}

entity_contexts = {}

system_modes = {}
system_priorities = {}

current_entity = None
current_phase = None
custom_types = {}

with open(SPEC) as f:
    current_system = None
    current_system_entity = None
    current_system_phase = None

    for line_num, raw_line in enumerate(f, 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("SOA "):
            parts = line.split()
            if len(parts) < 4:
                die(f"Línea {line_num}: Sintaxis SOA incorrecta. Uso: SOA <NombreTipo> <TipoBase> <comp1> <comp2> ...")
            type_name, base_type = parts[1], parts[2]
            components = parts[3:]
            SOA_TYPES[type_name] = {'base': base_type, 'comps': components}
            TYPE_MAP[type_name] = type_name 
            continue

        if line.startswith("BACKEND "):
            SELECTED_BACKEND = line.split()[1].lower()
            continue

        if line.startswith("CONFIG "):
            parts = line.split()
            if len(parts) >= 3:
                config_key = parts[1]
                config_value = parts[2]

                if config_key == "MAX_THREADS":
                    try:
                        MAX_THREADS = int(config_value)
                    except ValueError:
                        die(f"Línea {line_num}: Valor inválido para MAX_THREADS: {config_value}")
            continue

        if line.startswith("SYSTEM "):
            parts = line.split()
            if len(parts) < 2:
                die(f"Línea {line_num}: Sintaxis SYSTEM incorrecta")
            system_name = parts[1]
            current_system = system_name
            if system_name not in system_modes:
                system_modes[system_name] = "SINGLE"
            continue

        if line.startswith("PHASE ") and current_system:
            parts = line.split()
            if len(parts) < 2:
                die(f"Línea {line_num}: Sintaxis PHASE incorrecta")
            phase_name = parts[1]
            current_system_phase = phase_name
            continue

        if line.startswith("MODE ") and current_system:
            parts = line.split()
            if len(parts) < 2:
                die(f"Línea {line_num}: Sintaxis MODE incorrecta")
            mode_name = parts[1]
            if mode_name not in ["SINGLE", "PARALLEL"]:
                die(f"Línea {line_num}: Modo desconocido '{mode_name}', debe ser SINGLE o PARALLEL")
            system_modes[current_system] = mode_name
            continue

        if line.startswith("PRIORITY ") and current_system:
            parts = line.split()
            if len(parts) < 2:
                die(f"Línea {line_num}: Sintaxis PRIORITY incorrecta")
            try:
                system_priorities[current_system] = int(parts[1])
            except ValueError:
                die(f"Línea {line_num}: Prioridad debe ser un entero")
            continue

        if line.startswith("ENTITY ") and current_system:
            parts = line.split()
            if len(parts) < 2:
                die(f"Línea {line_num}: Sintaxis ENTITY incorrecta")
            entity_name = parts[1]
            if entity_name not in entities:
                die(f"Línea {line_num}: Entidad '{entity_name}' no definida")
            current_system_entity = entity_name
            continue

        if line.startswith("[TYPE "):
            parts = line[6:-1].split()
            if len(parts) != 2:
                die(f"Línea {line_num}: Sintaxis TYPE incorrecta")
            name, base = parts
            if base not in TYPE_MAP:
                die(f"Línea {line_num}: Tipo base desconocido '{base}'")
            TYPE_MAP[name] = TYPE_MAP[base]
            custom_types[name] = base
            continue

        # [STRICT] @@variable tipo [= valor]
        is_strict = False
        temp_line = line
        if temp_line.startswith("strict "):
            is_strict = True
            temp_line = temp_line[7:].strip()

        if temp_line.startswith("@@"):
            if not current_entity:
                die(f"Línea {line_num}: Variable fuera de entidad")

            if "=" in temp_line:
                decl, default_val = temp_line[2:].split("=", 1)
                decl = decl.strip()
                default_val = default_val.strip()
            else:
                decl = temp_line[2:].strip()
                default_val = None

            parts = decl.split()
            if len(parts) != 2:
                die(f"Línea {line_num}: Sintaxis variable incorrecta")
            var_name, var_type = parts

            if var_type not in TYPE_MAP:
                warn(f"Línea {line_num}: Tipo '{var_type}' no está en TYPE_MAP")
                
            target_dict = entities[current_entity]["shared_vars"] if current_phase == "SHARED" else entities[current_entity]["vars"]
            target_dict[var_name] = {"type": var_type, "default": default_val, "strict": is_strict}
            continue

        if line.endswith(":"):
            tag = line[:-1].strip()

            if current_system:
                if current_system_entity and current_system_phase:
                    entities[current_system_entity]["phases"][current_system_phase].append(current_system)
                    if current_system_entity in entity_contexts:
                        entity_contexts[current_system_entity]["systems"].add(current_system)
                elif current_system_phase:
                    globals[current_system_phase].append(current_system)

                current_system = None
                current_system_entity = None
                current_system_phase = None

            if tag in globals:
                current_phase = tag
                current_entity = None
                continue

            if tag.startswith("UNIQUE "):
                parts = tag.split()
                if len(parts) != 2:
                    die(f"Línea {line_num}: Sintaxis UNIQUE incorrecta")
                name = parts[1]
                entities[name] = {
                    "kind": "UNIQUE",
                    "phases": {k: [] for k in globals},
                    "vars": OrderedDict(),
                    "shared_vars": OrderedDict(),
                    "line": line_num
                }
                current_entity = name
                current_phase = None
                continue

            if tag.startswith("GENERIC "):
                parts = tag.split()
                if len(parts) != 3:
                    die(f"Línea {line_num}: Sintaxis GENERIC incorrecta")
                name = parts[1]
                count_expr = parts[2].split("=")[1]

                try:
                    count = int(count_expr)
                except ValueError:
                    die(f"Línea {line_num}: Count debe ser entero, got '{count_expr}'")

                if count <= 0:
                    die(f"Línea {line_num}: Count debe ser > 0")

                entities[name] = {
                    "kind": "GENERIC",
                    "count": count,
                    "phases": {k: [] for k in globals},
                    "vars": OrderedDict(),
                    "shared_vars": OrderedDict(),
                    "line": line_num
                }

                entity_contexts[name] = {
                    "variables": {},
                    "shared_variables": {},
                    "systems": set(),
                    "execution_order": []
                }

                current_entity = name
                current_phase = None
                continue

            if tag.startswith("SHARED "):
                parts = tag.split()
                if len(parts) != 2:
                    die(f"Línea {line_num}: Sintaxis SHARED incorrecta")
                entity_name = parts[1]

                if entity_name not in entities:
                    die(f"Línea {line_num}: Entidad '{entity_name}' no definida para SHARED properties")

                current_entity = entity_name
                current_phase = "SHARED"
                continue

            die(f"Línea {line_num}: Sección desconocida '{tag}'")
            continue

        if current_entity:
            if line in globals:
                current_phase = line
            elif current_phase == "SHARED":
                if line.startswith("@@"):
                    parts = line[2:].split()
                    if len(parts) != 2:
                        die(f"Línea {line_num}: Sintaxis variable SHARED incorrecta")
                    var_name, var_type = parts

                    if var_type not in TYPE_MAP:
                        die(f"Línea {line_num}: Tipo desconocido '{var_type}'")

                    entities[current_entity]["shared_vars"][var_name] = var_type
                else:
                    entities[current_entity]["phases"]["LOOP"].append(line)
                    if current_entity in entity_contexts:
                        entity_contexts[current_entity]["systems"].add(line)
            elif current_phase:
                entities[current_entity]["phases"][current_phase].append(line)
                if current_entity in entity_contexts:
                    entity_contexts[current_entity]["systems"].add(line)
            else:
                die(f"Línea {line_num}: Módulo sin fase para entidad {current_entity}")
        elif current_phase:
            globals[current_phase].append(line)
        else:
            if current_system:
                if line in entities:
                    current_system_entity = line
            else:
                warn(f"Línea {line_num}: Línea ignorada: {line}")

    if current_system:
        if current_system_entity and current_system_phase:
            entities[current_system_entity]["phases"][current_system_phase].append(current_system)
            if current_system_entity in entity_contexts:
                entity_contexts[current_system_entity]["systems"].add(current_system)
        elif current_system_phase:
            globals[current_system_phase].append(current_system)

def sort_systems_by_priority(sys_list):
    return sorted(sys_list, key=lambda x: system_priorities.get(x, 100))

for phase in globals:
    globals[phase] = sort_systems_by_priority(globals[phase])

for ent in entities.values():
    for phase in ent["phases"]:
        ent["phases"][phase] = sort_systems_by_priority(ent["phases"][phase])

for name, e in entities.items():
    e['_original_vars'] = e['vars'].copy()
    e['_original_shared_vars'] = e['shared_vars'].copy()

    def unroll_soa(vars_dict):
        new_dict = OrderedDict()
        for var_name, info in vars_dict.items():
            var_type = info["type"]
            default_val = info["default"]
            is_strict = info.get("strict", False)

            if var_type in SOA_TYPES and not is_strict:
                soa_info = SOA_TYPES[var_type]
                
                defaults = [None] * len(soa_info['comps'])
                if default_val and default_val.startswith('{') and default_val.endswith('}'):
                    raw_values = default_val[1:-1].split(',')
                    for i, val in enumerate(raw_values):
                        if i < len(defaults):
                            defaults[i] = val.strip()

                for i, comp in enumerate(soa_info['comps']):
                    new_dict[f"{var_name}_{comp}"] = {
                        "type": soa_info['base'],
                        "default": defaults[i]
                    }
            else:
                new_dict[var_name] = info
        return new_dict

    e["vars"] = unroll_soa(e["vars"])
    e["shared_vars"] = unroll_soa(e["shared_vars"])

if GSPEC:
    parse_gspec(GSPEC, entities, gspec_data)
    if not gspec_data['gcomponent']:
        die("GSPEC Error: No se pudo parsear un gcomponent válido del archivo GSPEC proporcionado.")

    if "RenderAllCubes" in globals["LOOP"]:
        globals["LOOP"].remove("RenderAllCubes")
    if "RenderScene" in globals["LOOP"]:
        globals["LOOP"].remove("RenderScene")

if "World" not in entities:
    die("Debe existir la entidad UNIQUE World")

REQ_PATTERN = re.compile(
    r'//\s*REQ:\s*'
    r'([a-zA-Z_][a-zA-Z0-9_]*)'
    r'\.'
    r'([a-zA-Z_][a-zA-Z0-9_]*)'
    r'(?:\s+as\s+([a-zA-Z_][a-zA-Z0-9_]*))?'
)


STRUCT_REQ_PATTERN = re.compile(
    r'//\s*REQ_STRUCT:\s*'
    r'([a-zA-Z_][a-zA-Z0-9_]*)'
    r'(?:\s+as\s+([a-zA-Z_][a-zA-Z0-9_]*))?'
)

all_modules = set()
for entity in entities.values():
    for phase_list in entity["phases"].values():
        all_modules.update(phase_list)
for phase_list in globals.values():
    all_modules.update(phase_list)

external_libs_needed = {}

module_info = {}
for mod in all_modules:
    path = f"{MODS}/{mod}.c"
    if not os.path.exists(path):
        die(f"Módulo '{mod}' no encontrado en {path}")

    reqs = []
    struct_reqs = []

    with open(path) as f:
        content = f.read()

        has_range_version = "range" in content.lower() and "_range" in mod.lower()

        for entity_name, var_name, alias in REQ_PATTERN.findall(content):
            if entity_name not in entities:
                die(f"{mod}: Entidad '{entity_name}' no definida en REQ")

            is_shared = var_name in entities[entity_name]['_original_shared_vars']
            original_vars_dict = entities[entity_name]['_original_shared_vars'] if is_shared else entities[entity_name]['_original_vars']
            
        for entity_name, var_name, alias in REQ_PATTERN.findall(content):
            if entity_name not in entities:
                die(f"{mod}: Entidad '{entity_name}' no definida en REQ")

            is_shared = var_name in entities[entity_name]['_original_shared_vars']
            original_vars_dict = entities[entity_name]['_original_shared_vars'] if is_shared else entities[entity_name]['_original_vars']
            
            is_internal = var_name in ["_active", "_capacity"]
            
            if var_name not in original_vars_dict and not is_internal:
                die(f"{mod}: Variable '{entity_name}.{var_name}' no declarada en el .spec")

            if is_internal:
                original_type_name = "int32"
                is_strict = True
            else:
                original_type_info = original_vars_dict[var_name]
                original_type_name = original_type_info['type']
                is_strict = original_type_info.get('strict', False)
            
            alias = alias or var_name

            if original_type_name in SOA_TYPES and not is_strict:
                soa_info = SOA_TYPES[original_type_name]
                for comp in soa_info['comps']:
                    reqs.append({
                        "type": "VAR",
                        "entity": entity_name,
                        "var": f"{var_name}_{comp}",
                        "alias": f"{alias}_{comp}",
                        "data_type": soa_info['base'],
                        "is_shared": is_shared
                    })
            else:
                reqs.append({
                    "type": "VAR",
                    "entity": entity_name,
                    "var": var_name,
                    "alias": alias,
                    "data_type": original_type_name,
                    "is_shared": is_shared
                })
                

        for match in STRUCT_REQ_PATTERN.finditer(content):
            entity_name, alias = match.groups()

            if entity_name not in entities:
                die(f"{mod}: Entidad '{entity_name}' no definida en REQ_STRUCT")

            struct_reqs.append({
                "type": "STRUCT",
                "entity": entity_name,
                "alias": alias or f"{entity_name}_data"
            })

        for lib_match in re.finditer(r'//\s*REQ_LIB:\s*([a-zA-Z0-9_/<>.-]+)', content):
            lib_name = lib_match.group(1).strip()
            import re as regex
            if lib_name.startswith('<') and lib_name.endswith('>'):
                lib_name = lib_name[1:-1]
            if lib_name.endswith('.h'):
                lib_name = lib_name[:-2]
            external_libs_needed[lib_name] = True

    module_info[mod] = {
        "reqs": reqs,
        "struct_reqs": struct_reqs,
        "path": path,
        "has_world_param": len(reqs) == 0 and len(struct_reqs) == 0,
        "is_range_version": has_range_version,
        "mode": system_modes.get(mod, "SINGLE")
    }

# GENERACIÓN DE CÓDIGO

with open(OUT, "w") as out:
    out.write("// GENERADO\n")
    out.write("#include <stdint.h>\n")
    out.write("#include <stdbool.h>\n")
    out.write("#include <string.h>\n")
    out.write("#include <math.h>\n")

    if GSPEC and gspec_data['gcomponent'] and SELECTED_BACKEND != "manual":
        out.write(f'#include "backend/backend_{SELECTED_BACKEND}.h"\n')

    if GSPEC and gspec_data['gcomponent']:
        out.write('\n#include "GraphicSystem/graphics_types.h"\n')
        out.write('#include "GraphicSystem/render_protocol.h"\n')
        out.write('#include "GraphicSystem/scene_sync_state.h"\n')

    if external_libs_needed:
        out.write("\n// Librerías externas requeridas por módulos\n")
        for lib in sorted(external_libs_needed.keys()):
            if ('/' in lib or '.' in lib) and not lib.startswith('<') and not lib.endswith('>'):

                if lib.endswith('.h') or lib.endswith('.c'):
                    out.write(f'#include "{lib}"\n')
                else:
                    out.write(f'#include "{lib}.h"\n')
            else:

                if lib.endswith('.h') or lib.endswith('.c'):
                    out.write(f"#include <{lib}>\n")
                else:
                    out.write(f"#include <{lib}.h>\n")
    out.write("\n")

    out.write("// Include for parallel execution\n")
    out.write('#include "MultithreadSupport/parallel.h"\n\n')

    out.write("// Include for graphics protocol and synchronization\n")
    out.write('#include "GraphicSystem/render_protocol.h"\n')
    out.write('#include "GraphicSystem/scene_sync_state.h"\n\n')

    out.write(f"// Configuration constants\n")
    out.write(f"#define GENERATED_MAX_THREADS {MAX_THREADS}\n\n")

    out.write("// Los tipos compuestos deben ser definidos por el usuario o incluidos via REQ_LIB\n\n")

    out.write("// Estructuras de entidades (contextos separados)\n")
    for name, e in entities.items():
        out.write(f"// Entidad: {name} ({e['kind']}")
        if e["kind"] == "GENERIC":
            out.write(f"[{e['count']}]")
        out.write(f")\n")
        out.write(f"typedef struct {{\n")
        
        if e["kind"] == "GENERIC":
            out.write("    int32_t _active;     // Instancias activas\n")
            out.write("    int32_t _capacity;   // Capacidad máxima\n")
        
        for var_name, info in sorted(e["vars"].items()):
            if var_name in ["_active", "_capacity"]: continue
            var_type = info["type"]
            c_type = TYPE_MAP.get(var_type, var_type)

            if e["kind"] == "GENERIC":
                out.write(f"    {c_type} {var_name}[{e['count']}];\n")
            else:
                out.write(f"    {c_type} {var_name};\n")

        for var_name, info in sorted(e["shared_vars"].items()):
            var_type = info["type"]
            c_type = TYPE_MAP.get(var_type, var_type)
            out.write(f"    {c_type} {var_name};  // Variable compartida\n")

        out.write(f"}} {name}_Data;\n\n")
    
    out.write("// Mundo con contextos separados\n")
    out.write("typedef struct {\n")
    out.write("    // Entidades (cada una con su propio contexto)\n")
    for name in entities:
        out.write(f"    {name}_Data {name.lower()};\n")
    
    out.write("\n    // Estado global del motor\n")
    out.write("    bool running;\n")
    out.write("    uint64_t frame;\n")
    out.write("    float delta_time;\n")
    
    out.write("    \n    // Variables globales automáticas\n")
    out.write("    struct {\n")
    out.write("        uint64_t start_time;\n")
    out.write("        uint64_t frame_time;\n")
    out.write("        int32_t fps;\n")
    out.write("        float frame_times[120];\n")
    out.write("        int32_t frame_time_index;\n")
    out.write("    } _engine;\n")
    
    out.write("} World;\n\n")

    if GSPEC and gspec_data['gcomponent']:
        out.write("// Datos de la escena para renderizado\n")
        out.write("SceneData s = {0};\n")
        out.write("SceneSyncState ss = {0};\n\n")
    
# prototipos
    out.write("// Prototipos de sistemas\n")
    out.write("// Nota: Cada sistema recibe solo los datos que necesita\n")
    if GSPEC and gspec_data['gcomponent']:
        gcomp_entity = gspec_data['entity']
        out.write(f"void sys_sync_gcomponent_{gcomp_entity}_range(World* w, SceneData* s, SceneSyncState* ss, int start, int end);\n")
        out.write(f"void sys_sync_gcomponent_{gcomp_entity}(World* w, SceneData* s, SceneSyncState* ss);\n")
    out.write("//       No hay acceso accidental entre entidades\n\n")

    for mod, info in sorted(module_info.items()):
        if info["mode"] == "PARALLEL":
            out.write(f"void system_{mod}_range(World* w, int start, int end);\n")

        if info["has_world_param"]:
            out.write(f"void system_{mod}(World* w);\n")
        else:
            params = []

            for req in info["reqs"]:
                c_type = TYPE_MAP.get(req["data_type"], req["data_type"])
                entity_kind = entities[req["entity"]]["kind"]

                if entity_kind == "GENERIC" and not req['is_shared']:
                    params.append(f"{c_type}* {req['alias']}")
                else:
                    params.append(f"{c_type}* {req['alias']}")

            for req in info["struct_reqs"]:
                params.append(f"{req['entity']}_Data* {req['alias']}")

            out.write(f"void system_{mod}({', '.join(params)});\n")

    out.write("\n")
    
    out.write("// Implementaciones\n")
    all_modules_to_include = set(module_info.keys())

    for mod, info in module_info.items():
        if info["mode"] == "PARALLEL":
            all_modules_to_include.add(mod)

    for mod in sorted(all_modules_to_include):
        out.write(f'#include "{MODS}/{mod}.c"\n')
    if GSPEC and gspec_data['gcomponent']:
        out.write('#include "backend/backend_raylib.c"\n')
    out.write("\n")

    if GSPEC and gspec_data['gcomponent']:
        gcomp_entity = gspec_data['entity']
        gcomp_entity_lower = gcomp_entity.lower()
        entity_count = entities[gcomp_entity]['count']

        out.write(f"// Implementación de la función de sincronización GSPEC\n")
        out.write(f"void sys_sync_gcomponent_{gcomp_entity}_range(World* w, SceneData* s, SceneSyncState* ss, int start, int end) {{\n")
        out.write(f"    for (int i = start; i < end; i++) {{\n")

        if gspec_data['visibility']:
            vis_when_var = gspec_data['visibility']['when']
            out.write(f"        // Visibilidad\n")
            out.write(f"        bool is_visible = w->{gcomp_entity_lower}.{vis_when_var}[i];\n")
            out.write(f"        uint8_t target_alpha = is_visible ? 255 : 0;\n")
            out.write(f"        if (s->instances[i].color.a != target_alpha) {{\n")
            out.write(f"            s->instances[i].color.a = target_alpha;\n")
            out.write(f"            scene_sync_mark(ss, i);\n")
            out.write(f"        }}\n")
            out.write(f"        if (!is_visible) continue;\n")

        if gspec_data['transform']:
            trans_update_when = gspec_data['transform'].get('update_when')
            if trans_update_when:
                out.write(f"        // Actualizar Transformación solo si {trans_update_when} es verdadero\n")
                out.write(f"        if (!w->{gcomp_entity_lower}.{trans_update_when}[i]) {{\n")
                out.write(f"            // Si no está activo y la transformación no necesita actualizarse, solo marcar como dirty si la visibilidad cambió\n")
                out.write(f"            // (la lógica de visibilidad ya manejó esto)\n")
                out.write(f"        }} else {{\n")

            trans_from_fields = [f.strip() for f in gspec_data['transform']['from'].split(',')]
            
            actual_x_var = f"{trans_from_fields[0].split('.')[0]}_{trans_from_fields[0].split('.')[1]}"
            actual_y_var = f"{trans_from_fields[1].split('.')[0]}_{trans_from_fields[1].split('.')[1]}"
            actual_z_var = f"{trans_from_fields[2].split('.')[0]}_{trans_from_fields[2].split('.')[1]}"


            out.write(f"        // Transformación (traslación)\n")
            out.write(f"        float _px = w->{gcomp_entity_lower}.{actual_x_var}[i];\n")
            out.write(f"        float _py = w->{gcomp_entity_lower}.{actual_y_var}[i];\n")
            out.write(f"        float _pz = w->{gcomp_entity_lower}.{actual_z_var}[i];\n")
            out.write(f"        if (s->instances[i].transform.m[12] != _px || s->instances[i].transform.m[13] != _py || s->instances[i].transform.m[14] != _pz) {{\n")
            out.write(f"            s->instances[i].transform.m[12] = _px;\n")
            out.write(f"            s->instances[i].transform.m[13] = _py;\n")
            out.write(f"            s->instances[i].transform.m[14] = _pz;\n")
            out.write(f"            scene_sync_mark(ss, i);\n")
            out.write(f"        }}\n")

            if trans_update_when:
                out.write(f"        }}\n")

        if gspec_data['color']:
            color_from_var = gspec_data['color']['from']
            out.write(f"        // Color\n")
            out.write(f"        uint32_t current_w_color = w->{gcomp_entity_lower}.{color_from_var}[i];\n")
            out.write(f"        uint8_t _r = (uint8_t)(current_w_color >> 16);\n")
            out.write(f"        uint8_t _g = (uint8_t)(current_w_color >> 8);\n")
            out.write(f"        uint8_t _b = (uint8_t)current_w_color;\n")
            out.write(f"        if (s->instances[i].color.r != _r || s->instances[i].color.g != _g || s->instances[i].color.b != _b) {{\n")
            out.write(f"            s->instances[i].color.r = _r;\n")
            out.write(f"            s->instances[i].color.g = _g;\n")
            out.write(f"            s->instances[i].color.b = _b;\n")
            out.write(f"            scene_sync_mark(ss, i);\n")
            out.write(f"        }}\n")

        out.write(f"    }}\n")
        out.write(f"}}\n\n")

        out.write(f"// Wrapper para la función de sincronización GSPEC\n")
        out.write(f"void sys_sync_gcomponent_{gcomp_entity}(World* w, SceneData* s, SceneSyncState* ss) {{\n")
        out.write(f"    uint32_t active_count = w->{gcomp_entity_lower}._active;\n")
        out.write(f"    scene_ensure_capacity(s, active_count);\n")
        out.write(f"    s->count = active_count;\n")
        out.write(f"    sys_sync_gcomponent_{gcomp_entity}_range(w, s, ss, 0, active_count);\n")
        out.write(f"}}\n\n")

    out.write("// Wrappers para sistemas paralelos\n")
    for mod, info in sorted(module_info.items()):
        if info["mode"] == "PARALLEL":
            generic_entity_name = None
            for entity_name, entity_data in entities.items():
                if entity_data["kind"] == "GENERIC":
                    generic_entity_name = entity_name
                    break

            if generic_entity_name:
                out.write(f"void system_{mod}(World* w) {{\n")
                out.write(f"    parallel_run(w, (SystemRangeFn)system_{mod}_range, w->{generic_entity_name.lower()}._active);\n")
                out.write(f"}}\n\n")
            else:
                out.write(f"void system_{mod}(World* w) {{\n")
                out.write(f"    // No GENERIC entity found for parallel execution\n")
                out.write(f"}}\n\n")
    
    out.write("// Inicialización del mundo automática (Procedural)\n")
    out.write("static void init_world(World* w) {\n")
    out.write("    memset(w, 0, sizeof(World));\n")
    out.write("    w->running = true;\n")
    out.write("    w->frame = 0;\n")
    out.write("    w->delta_time = 0.016f;\n")
    out.write("    w->_engine.fps = 60;\n")
    out.write("    w->_engine.frame_time_index = 0;\n\n")
    
    for name, e in entities.items():
        if e["kind"] != "UNIQUE": continue
        name_l = name.lower()
        for var_name, info in sorted(e["vars"].items()):
            if info["default"] is not None:
                val = info["default"]
                c_type = TYPE_MAP.get(info["type"], info["type"])
                if val.startswith('{'): val = f"({c_type}){val}"
                out.write(f"    w->{name_l}.{var_name} = {val};\n")
        for var_name, info in sorted(e["shared_vars"].items()):
            if info["default"] is not None:
                val = info["default"]
                c_type = TYPE_MAP.get(info["type"], info["type"])
                if val.startswith('{'): val = f"({c_type}){val}"
                out.write(f"    w->{name_l}.{var_name} = {val};\n")

    for name, e in entities.items():
        if e["kind"] != "GENERIC": continue
        name_l = name.lower()
        out.write(f"\n    // Inicializando {name}\n")
        out.write(f"    w->{name_l}._capacity = {e['count']};\n")
        
        active_val = "0"
        if "_active" in e["vars"] and e["vars"]["_active"]["default"] is not None:
            active_val = e["vars"]["_active"]["default"]
        out.write(f"    w->{name_l}._active = {active_val};\n")
        
        vars_to_init = []
        for var_name, info in sorted(e["vars"].items()):
            if var_name == "_active": continue
            if info["default"] is not None:
                val = info["default"].strip()
                
                def is_zero_val(v):
                    v = v.strip()
                    if v in ["0", "0.0", "0.0f", "0.00f", "false", "NULL"]: return True
                    if v.startswith("{") and v.endswith("}"):
                        content = v[1:-1]
                        parts = content.split(",")
                        for p in parts:
                            if not is_zero_val(p): return False
                        return True
                    return False

                if not is_zero_val(val):
                    vars_to_init.append((var_name, info))
        
        if vars_to_init:
            out.write(f"    for(int i=0; i<{e['count']}; i++) {{\n")
            for var_name, info in vars_to_init:
                val = info["default"]
                c_type = TYPE_MAP.get(info["type"], info["type"])
                if val.startswith('{'): val = f"({c_type}){val}"
                out.write(f"        w->{name_l}.{var_name}[i] = {val};\n")
            out.write(f"    }}\n")

        for var_name, info in sorted(e["shared_vars"].items()):
            if info["default"] is not None:
                val = info["default"]
                c_type = TYPE_MAP.get(info["type"], info["type"])
                if val.startswith('{'): val = f"({c_type}){val}"
                out.write(f"    w->{name_l}.{var_name} = {val};\n")
    
    out.write("}\n\n")

    out.write("// Helper para construir argumentos de sistemas\n")
    out.write("// Garantiza que cada entidad acceda solo a sus propios datos\n")
    out.write("static void build_system_args_entity(World* w, int32_t entity_index, ")
    out.write("const char* entity_name, const char* system_name, ")
    out.write("void (*system_func)(...)) {\n")
    out.write("    // Esta función asegura el cableado correcto\n")
    out.write("    // Cada entidad tiene su propio índice y contexto\n")
    out.write("    (void)w; (void)entity_index; (void)entity_name;\n")
    out.write("    (void)system_name; (void)system_func;\n")
    out.write("}\n\n")

    out.write("int main(void) {\n")
    out.write("    static World w;\n")
    out.write("    init_world(&w);\n\n")
    if GSPEC:
        initial_capacity = 256
        for e in entities.values():
            if e['kind'] == 'GENERIC':
                initial_capacity = e['count']
                break
        out.write(f"    scene_init(&s, {initial_capacity});\n\n")
    
    # PRE_START
    if globals["PRE_START"]:
        out.write("    // ========== PRE_START (Configuración) ==========\n")
        for mod in globals["PRE_START"]:
            info = module_info[mod]
            if info["has_world_param"]:
                out.write(f"    system_{mod}(&w);\n")
            else:
                args = []
                for req in info["reqs"]:
                    ent_name = req["entity"]
                    var_name = req["var"]
                    ent = entities[ent_name]
                    is_shared = req.get("is_shared", False)
                    
                    if ent["kind"] == "GENERIC" and not is_shared:
                        if var_name in ["_active", "_capacity"]:
                            args.append(f"&w.{ent_name.lower()}.{var_name}")
                        else:
                            args.append(f"&w.{ent_name.lower()}.{var_name}[0]")
                    else:
                        args.append(f"&w.{ent_name.lower()}.{var_name}")
                
                for req in info["struct_reqs"]:
                    args.append(f"&w.{req['entity'].lower()}")
                
                out.write(f"    system_{mod}({', '.join(args)});\n")
        out.write("\n")
    
    # START
    out.write("    // ========== START (Inicialización) ==========\n")
    # Global START
    for mod in globals["START"]:
        info = module_info[mod]
        if info["has_world_param"]:
            out.write(f"    system_{mod}(&w);\n")
        else:
            args = []
            for req in info["reqs"]:
                ent_name = req["entity"]
                var_name = req["var"]
                ent = entities[ent_name]
                is_shared = req.get("is_shared", False)

                if ent["kind"] == "GENERIC" and not is_shared:
                    if var_name in ["_active", "_capacity"]:
                        args.append(f"&w.{ent_name.lower()}.{var_name}")
                    else:
                        args.append(f"&w.{ent_name.lower()}.{var_name}[0]")
                else:
                    args.append(f"&w.{ent_name.lower()}.{var_name}")
            
            for req in info["struct_reqs"]:
                args.append(f"&w.{req['entity'].lower()}")
            
            out.write(f"    system_{mod}({', '.join(args)});\n")
        
    for name, e in entities.items():
        if e["phases"]["START"]:
            out.write(f"\n    // --- {name}.START (Contexto específico) ---\n")
            
            if e["kind"] == "GENERIC":
                out.write(f"    for (int32_t i = 0; i < w.{name.lower()}._active; i++) {{\n")
                out.write(f"        // Instancia {name}[i] se inicializa\n")
                
                for mod in e["phases"]["START"]:
                    info = module_info[mod]
                    if info["has_world_param"]:
                        out.write(f"        system_{mod}(&w);\n")
                    else:
                        args = []
                        for req in info["reqs"]:
                            ent_name = req["entity"]
                            var_name = req["var"]
                            ent2 = entities[ent_name]
                            
                            # IMPORTANTE: Solo esta entidad usa su índice 'i'
                            # Otras entidades usan índice 0 o estructura completa
                            if ent2["kind"] == "GENERIC" and not is_shared:
                                if ent_name == name:
                                    # Misma entidad: usa índice actual
                                    if var_name in ["_active", "_capacity"]:
                                        args.append(f"&w.{ent_name.lower()}.{var_name}")
                                    else:
                                        args.append(f"&w.{ent_name.lower()}.{var_name}[i]")
                                else:
                                    # Entidad diferente: ¡NO USAR 'i'!
                                    # Usar estructura completa o índice 0 según REQ
                                    has_struct = any(r["type"] == "STRUCT" and r["entity"] == ent_name 
                                                   for r in info["struct_reqs"])
                                    if has_struct:
                                        args.append(f"&w.{ent_name.lower()}")
                                    else:
                                        if var_name in ["_active", "_capacity"]:
                                            args.append(f"&w.{ent_name.lower()}.{var_name}")
                                        else:
                                            args.append(f"&w.{ent_name.lower()}.{var_name}[0]")
                            else:
                                args.append(f"&w.{ent_name.lower()}.{var_name}")
                        

                        for req in info["struct_reqs"]:
                            args.append(f"&w.{req['entity'].lower()}")
                        
                        out.write(f"        system_{mod}({', '.join(args)});\n")
                
                out.write("    }\n")
            else:

                for mod in e["phases"]["START"]:
                    info = module_info[mod]
                    if info["has_world_param"]:
                        out.write(f"    system_{mod}(&w);\n")
                    else:
                        args = []
                        for req in info["reqs"]:
                            ent_name = req["entity"]
                            var_name = req["var"]
                            ent2 = entities[ent_name]
                            
                            if ent2["kind"] == "GENERIC" and not req['is_shared']:
                                has_struct = any(r["type"] == "STRUCT" and r["entity"] == ent_name 
                                               for r in info["struct_reqs"])
                                if has_struct:
                                    args.append(f"&w.{ent_name.lower()}")
                                else:
                                    args.append(f"&w.{ent_name.lower()}.{var_name}[0]")
                            else:
                                args.append(f"&w.{ent_name.lower()}.{var_name}")
                        
                        for req in info["struct_reqs"]:
                            args.append(f"&w.{req['entity'].lower()}")
                        
                        out.write(f"    system_{mod}({', '.join(args)});\n")
    
    out.write("\n    // ========== LOOP PRINCIPAL ==========\n")
    out.write("    while (w.running) {\n")
    out.write("        w.frame++;\n")
    if GSPEC and gspec_data['gcomponent']:
        out.write("        scene_sync_reset(&ss);\n\n")
    
    # Global LOOP
    if globals["LOOP"]:
        out.write("        // --- Global.LOOP ---\n")
        for mod in globals["LOOP"]:
            info = module_info[mod]
            if info["has_world_param"]:
                out.write(f"        system_{mod}(&w);\n")
            else:
                args = []
                for req in info["reqs"]:
                    ent_name = req["entity"]
                    var_name = req["var"]
                    ent = entities[ent_name]
                    is_shared = req.get("is_shared", False)
                    
                    if ent["kind"] == "GENERIC" and not is_shared:
                        if var_name in ["_active", "_capacity"]:
                            args.append(f"&w.{ent_name.lower()}.{var_name}")
                        else:
                            args.append(f"&w.{ent_name.lower()}.{var_name}[0]")
                    else:
                        args.append(f"&w.{ent_name.lower()}.{var_name}")
                
                for req in info["struct_reqs"]:
                    args.append(f"&w.{req['entity'].lower()}")
                
                out.write(f"        system_{mod}({', '.join(args)});\n")
        out.write("\n")
    
    if GSPEC and gspec_data['gcomponent'] and SELECTED_BACKEND != "manual":
        gcomp_entity = gspec_data['entity']
        gcomp_entity_lower = gcomp_entity.lower()
        
        out.write(f"        // Sincronización GSPEC Automática ({SELECTED_BACKEND})\n")
        out.write(f"        sys_sync_gcomponent_{gcomp_entity}(&w, &s, &ss);\n")

        out.write(f"        // Actualizar búfer de GPU y Dibujar\n")
        out.write(f"        backend_{SELECTED_BACKEND}_update_gpu(&w.world.vbo_id, &s, &ss);\n")

        out.write(f"        backend_{SELECTED_BACKEND}_draw_instanced(w.world.cube_model, &s);\n") 
        out.write("\n")

    for name, e in entities.items():
        if e["phases"]["LOOP"]:
            out.write(f"        // --- {name}.LOOP (Contexto propio) ---\n")
            
            if e["kind"] == "GENERIC":
                out.write(f"        for (int32_t i_{name} = 0; i_{name} < w.{name.lower()}._active; i_{name}++) {{\n")
                out.write(f"            // Procesando {name}[i_{name}]\n")
                
                for mod in e["phases"]["LOOP"]:
                    info = module_info[mod]
                    if info["has_world_param"]:
                        out.write(f"            system_{mod}(&w);\n")
                    else:
                        args = []
                        for req in info["reqs"]:
                            ent_name = req["entity"]
                            var_name = req["var"]
                            ent2 = entities[ent_name]
                            
                            if ent2["kind"] == "GENERIC" and not req['is_shared']:
                                if ent_name == name:
                                    args.append(f"&w.{ent_name.lower()}.{var_name}[i_{name}]")
                                else:
                                    # Entidad diferente: ¡NUNCA usar i_nombre!
                                    # Usar REQ_STRUCT si existe, sino índice 0
                                    uses_struct = any(r["type"] == "STRUCT" and r["entity"] == ent_name 
                                                    for r in info["struct_reqs"])
                                    if uses_struct:
                                        args.append(f"&w.{ent_name.lower()}")
                                    else:
                                        args.append(f"&w.{ent_name.lower()}.{var_name}[0]")
                            else:
                                args.append(f"&w.{ent_name.lower()}.{var_name}")
                        
                        for req in info["struct_reqs"]:
                            args.append(f"&w.{req['entity'].lower()}")
                        
                        out.write(f"            system_{mod}({', '.join(args)});\n")
                
                out.write("        }\n")
            else:
                for mod in e["phases"]["LOOP"]:
                    info = module_info[mod]
                    if info["has_world_param"]:
                        out.write(f"        system_{mod}(&w);\n")
                    else:
                        args = []
                        for req in info["reqs"]:
                            ent_name = req["entity"]
                            var_name = req["var"]
                            ent2 = entities[ent_name]
                            
                            if ent2["kind"] == "GENERIC" and not req['is_shared']:
                                # Para acceder a GENERIC desde UNIQUE
                                uses_struct = any(r["type"] == "STRUCT" and r["entity"] == ent_name 
                                               for r in info["struct_reqs"])
                                if uses_struct:
                                    args.append(f"&w.{ent_name.lower()}")
                                else:
                                    args.append(f"&w.{ent_name.lower()}.{var_name}[0]")
                            else:
                                args.append(f"&w.{ent_name.lower()}.{var_name}")
                        
                        for req in info["struct_reqs"]:
                            args.append(f"&w.{req['entity'].lower()}")
                        
                        out.write(f"        system_{mod}({', '.join(args)});\n")
            out.write("\n")
    
    if globals["POST_LOOP"]:
        out.write("        // --- Global.POST_LOOP ---\n")
        for mod in globals["POST_LOOP"]:
            info = module_info[mod]
            if info["has_world_param"]:
                out.write(f"        system_{mod}(&w);\n")
            else:
                args = []
                for req in info["reqs"]:
                    ent_name = req["entity"]
                    var_name = req["var"]
                    ent = entities[ent_name]
                    is_shared = req.get("is_shared", False)
                    
                    if ent["kind"] == "GENERIC" and not is_shared:
                        if var_name in ["_active", "_capacity"]:
                            args.append(f"&w.{ent_name.lower()}.{var_name}")
                        else:
                            args.append(f"&w.{ent_name.lower()}.{var_name}[0]")
                    else:
                        args.append(f"&w.{ent_name.lower()}.{var_name}")
                
                for req in info["struct_reqs"]:
                    args.append(f"&w.{req['entity'].lower()}")
                
                out.write(f"        system_{mod}({', '.join(args)});\n")
        out.write("\n")
    
    out.write("    }\n\n")
    
    # END
    out.write("    // ========== END (Limpieza) ==========\n")
    # Entity END primero
    for name, e in reversed(list(entities.items())):
        if e["phases"]["END"]:
            out.write(f"\n    // --- {name}.END ---\n")
            
            if e["kind"] == "GENERIC":
                out.write(f"    for (int32_t i = 0; i < w.{name.lower()}._active; i++) {{\n")
                for mod in e["phases"]["END"]:
                    info = module_info[mod]
                    if info["has_world_param"]:
                        out.write(f"        system_{mod}(&w);\n")
                    else:
                        args = []
                        for req in info["reqs"]:
                            ent_name = req["entity"]
                            var_name = req["var"]
                            ent2 = entities[ent_name]
                            
                            if ent2["kind"] == "GENERIC" and not req['is_shared']:
                                if ent_name == name:
                                    args.append(f"&w.{ent_name.lower()}.{var_name}[i]")
                                else:
                                    uses_struct = any(r["type"] == "STRUCT" and r["entity"] == ent_name 
                                                    for r in info["struct_reqs"])
                                    if uses_struct:
                                        args.append(f"&w.{ent_name.lower()}")
                                    else:
                                        args.append(f"&w.{ent_name.lower()}.{var_name}[0]")
                            else:
                                args.append(f"&w.{ent_name.lower()}.{var_name}")
                        
                        for req in info["struct_reqs"]:
                            args.append(f"&w.{req['entity'].lower()}")
                        
                        out.write(f"        system_{mod}({', '.join(args)});\n")
                out.write("    }\n")
            else:
                for mod in e["phases"]["END"]:
                    info = module_info[mod]
                    if info["has_world_param"]:
                        out.write(f"    system_{mod}(&w);\n")
                    else:
                        args = []
                        for req in info["reqs"]:
                            ent_name = req["entity"]
                            var_name = req["var"]
                            ent2 = entities[ent_name]
                            
                            if ent2["kind"] == "GENERIC" and not req['is_shared']:
                                uses_struct = any(r["type"] == "STRUCT" and r["entity"] == ent_name 
                                               for r in info["struct_reqs"])
                                if uses_struct:
                                    args.append(f"&w.{ent_name.lower()}")
                                else:
                                    args.append(f"&w.{ent_name.lower()}.{var_name}[0]")
                            else:
                                args.append(f"&w.{ent_name.lower()}.{var_name}")
                        
                        for req in info["struct_reqs"]:
                            args.append(f"&w.{req['entity'].lower()}")
                        
                        out.write(f"        system_{mod}({', '.join(args)});\n")
    
    if globals["END"]:
        out.write("\n    // --- Global.END ---\n")
        for mod in globals["END"]:
            info = module_info[mod]
            if info["has_world_param"]:
                out.write(f"    system_{mod}(&w);\n")
            else:
                args = []
                for req in info["reqs"]:
                    ent_name = req["entity"]
                    var_name = req["var"]
                    ent = entities[ent_name]
                    is_shared = req.get("is_shared", False)
                    
                    if ent["kind"] == "GENERIC" and not is_shared:
                        if var_name in ["_active", "_capacity"]:
                            args.append(f"&w.{ent_name.lower()}.{var_name}")
                        else:
                            args.append(f"&w.{ent_name.lower()}.{var_name}[0]")
                    else:
                        args.append(f"&w.{ent_name.lower()}.{var_name}")
                
                for req in info["struct_reqs"]:
                    args.append(f"&w.{req['entity'].lower()}")
                
                out.write(f"        system_{mod}({', '.join(args)});\n")

    if GSPEC:
        out.write("    scene_free(&s);\n")

    out.write("\n    return 0;\n")
    out.write("}\n")
    print("Builder: código generado con éxito")
