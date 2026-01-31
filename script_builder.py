#!/usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import re
from dataclasses import dataclass, field
from typing import List, Dict, Set

RULES_DIR = "rules"
OUT_DIR = "modules"

KEYWORDS = {
    "sin", "cos", "tan", "sqrt", "pow", "fabs", "fmin", "fmax", "floor", "ceil",
    "clamp", "lerp", "abs", "true", "false", "NULL", "if", "else", "return",
    "i", "start", "end", "w"
}

TYPE_MAP = {
    "active": "bool", "is_awake": "bool", "color": "int",
    "health": "int", "ammo": "int", "id": "uint32_t", "team_id": "int"
}

@dataclass
class Variable:
    alias: str
    source_entity: str
    source_prop: str
    c_type: str
    is_array: bool
    access: str  # READ | WRITE | READ_WRITE

@dataclass
class Rule:
    name: str
    conditions: List[str] = field(default_factory=list)
    actions: List[str] = field(default_factory=list)

@dataclass
class ModuleSpec:
    name: str
    entity: str
    reqs: Dict[str, Variable] = field(default_factory=dict)
    rules: List[Rule] = field(default_factory=list)

class RuleParser:
    def __init__(self, filepath):
        self.filepath = filepath
        self.module = None
        self.current_rule = None

    def _resolve_type(self, prop):
        return TYPE_MAP.get(prop, "float")

    def parse(self) -> ModuleSpec:
        name = os.path.splitext(os.path.basename(self.filepath))[0]
        self.module = ModuleSpec(name=name, entity="Unknown")

        with open(self.filepath, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines()]

        mode = "HEADER"
        for line in lines:
            if not line or line.startswith(("#", "//")): continue

            if line.upper() == "CONDITIONS:": mode = "CONDITIONS"; continue
            if line.upper() == "ACTIONS:": mode = "ACTIONS"; continue
            if line.upper().startswith("RULE:"):
                self._finalize_rule()
                self.current_rule = Rule(name=line.split(":", 1)[1].strip())
                mode = "HEADER"
                continue

            if mode == "HEADER":
                parts = line.split()
                if not parts: continue
                cmd = parts[0].upper()
                if cmd == "MODULE_ENTITY:":
                    self.module.entity = parts[1]
                elif cmd == "REQ:":
                    self._parse_req(line)

            elif mode == "CONDITIONS" and self.current_rule:
                clean = re.sub(r'^(WHEN|AND|OR|NOT)\s+', '', line, flags=re.I)
                self.current_rule.conditions.append(clean)

            elif mode == "ACTIONS" and self.current_rule:
                self.current_rule.actions.append(line)

        self._finalize_rule()
        return self.module

    def _finalize_rule(self):
        if self.current_rule:
            self.module.rules.append(self.current_rule)
            self.current_rule = None

    def _parse_req(self, line):
        # Nuevo formato: REQ: Entity.prop as alias [ARRAY|SINGLE] [READ|WRITE|READ_WRITE]
        m = re.search(r'REQ:\s+(\w+)\.(\w+)\s+as\s+(\w+)(?:\s+(ARRAY|SINGLE))?(?:\s+(READ|WRITE|READ_WRITE))?', line, re.I)
        if not m: raise ValueError(f"Error sintáctico en REQ: {line}")

        ent, prop, alias, mode, access = m.groups()
        # Si no se especifica, ARRAY si es la entidad del modulo, sino SINGLE
        if mode is None:
            is_array = (ent == self.module.entity)
        else:
            is_array = (mode.upper() == "ARRAY")

        self.module.reqs[alias] = Variable(
            alias=alias, source_entity=ent, source_prop=prop,
            c_type=self._resolve_type(prop), is_array=is_array,
            access=(access or "READ").upper()
        )

class CGenerator:
    def __init__(self, module: ModuleSpec):
        self.m = module

    def transpile_expr(self, expr: str) -> str:
        def repl(match):
            tok = match.group(0)
            if tok.isdigit() or tok in KEYWORDS: return tok
            if tok in self.m.reqs:
                v = self.m.reqs[tok]
                return f"{tok}[i]" if v.is_array else f"(*{tok})"
            return tok
        return re.sub(r'\b[a-zA-Z_]\w*\b', repl, expr)

    def generate_action(self, line: str) -> str:
        if line.upper().startswith("SET "):
            content = line[4:].strip()
            if '=' not in content: return f"// ERROR: SET sin '='"
            tgt, expr_raw = content.split('=', 1)
            tgt = tgt.strip()
            expr = self.transpile_expr(expr_raw.strip())

            if tgt not in self.m.reqs: return f"{tgt} = {expr};"
            v = self.m.reqs[tgt]
            if "WRITE" not in v.access: return f'#error "Intento de escritura en variable READ: {tgt}"'

            return f"{tgt}[i] = {expr};" if v.is_array else f"(*{tgt}) = {expr};"

        if line.upper().startswith("EMIT "):
            tokens = line.split()
            name = tokens[1]
            args = [self.transpile_expr(a) for a in tokens[2:]]
            while len(args) < 3: args.append("0")
            return f"emit_custom_event({name}, {args[0]}, {args[1]}, {args[2]});"

        if line.upper() == "DESTROY": return "script_destroy_self(i);"

        return self.transpile_expr(line) + ";"

    def generate(self) -> str:
        out = [f"// MODULE: sys_{self.m.name}", "#include <math.h>", "#include <stdbool.h>", '#include "GraphicSystem/graphics_types.h"', '#include "ScriptSupport/scriptsupport.h"', ""]
        out.append(f"void system_sys_{self.m.name}_range(World* w, int start, int end) {{")

        # Unpacking
        for v in self.m.reqs.values():
            src = "world" if v.source_entity == "World" else v.source_entity.lower()
            prefix = "const " if "WRITE" not in v.access and not v.is_array else ""
            if v.source_entity == "World":
                out.append(f"    {prefix}{v.c_type}* {v.alias} = &w->world.{v.source_prop};")
            else:
                out.append(f"    {prefix}{v.c_type}* {v.alias} = w->{src}.{v.source_prop};")

        out.append("\n    for (int i = start; i < end; i++) {")

        # El fix del active: solo si la entidad tiene active registrado
        has_active = any(v.source_prop == "active" and v.source_entity == self.m.entity for v in self.m.reqs.values())
        if has_active:
            out.append(f"        if (!w->{self.m.entity.lower()}.active[i]) continue;")

        for r in self.m.rules:
            cond = " && ".join(f"({self.transpile_expr(c)})" for c in r.conditions) or "true"
            out.append(f"        if ({cond}) {{")
            for a in r.actions:
                out.append(f"            {self.generate_action(a)}")
            out.append("        }")

        out.append("    }\n}")
        return "\n".join(out)

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for f in os.listdir(RULES_DIR):
        if f.endswith(".rule"):
            spec = RuleParser(os.path.join(RULES_DIR, f)).parse()
            with open(os.path.join(OUT_DIR, f"sys_{spec.name}.c"), "w") as o:
                o.write(CGenerator(spec).generate())
            print(f"[OK] {f}")

if __name__ == "__main__": main()
