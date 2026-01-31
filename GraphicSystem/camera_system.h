

/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */


#ifndef CAMERA_SYSTEM_H
#define CAMERA_SYSTEM_H

#include "raylib.h"
#include <stdbool.h>

// Definición estática de la cámara para que sea compartida por los módulos que incluyan este header en main.c
static Camera3D _global_camera = {
    .position = { 0.0f, 20.0f, 20.0f },
    .target = { 0.0f, 0.0f, 0.0f },
    .up = { 0.0f, 1.0f, 0.0f },
    .fovy = 45.0f,
    .projection = CAMERA_PERSPECTIVE
};

static inline Camera3D* get_current_camera() {
    return &_global_camera;
}

#endif
