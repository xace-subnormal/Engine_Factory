

/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

#ifndef GRAPHICS_TYPES_H
#define GRAPHICS_TYPES_H

#include <stdint.h>
#include <stdbool.h>

// Definición de tipos básicos SOLO si no se han definido antes (Headless mode)
#ifndef RL_VECTOR3_TYPE
typedef struct Vector3 { float x; float y; float z; } Vector3;
#define RL_VECTOR3_TYPE
#endif

#ifndef RL_VECTOR2_TYPE
typedef struct Vector2 { float x; float y; } Vector2;
#define RL_VECTOR2_TYPE
#endif

#ifndef RL_MATRIX_TYPE
typedef struct Matrix {
    float m0, m4, m8, m12;
    float m1, m5, m9, m13;
    float m2, m6, m10, m14;
    float m3, m7, m11, m15;
} Matrix;
#define RL_MATRIX_TYPE
#endif

typedef struct { float m[16]; } mat4_raw;
typedef struct { uint8_t r, g, b, a; } color_rgba8;

typedef struct {
    mat4_raw transform;
    color_rgba8 color;
} RenderInstance;

typedef struct {
    RenderInstance* instances;
    uint32_t count;
    uint32_t capacity;
} SceneData;

#endif
