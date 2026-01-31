

/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */


#ifndef BACKEND_RAYLIB_H
#define BACKEND_RAYLIB_H

#include "raylib.h"
#include "../GraphicSystem/graphics_types.h"

void backend_raylib_draw_instanced(Model model, const SceneData* s);

// Sincroniza el buffer de la CPU (s) con la GPU, recreando el buffer si es necesario.
// Actualiza el VBO ID a través de un puntero si este es recreado.
void backend_raylib_update_gpu(unsigned int* vbo_id_ptr, const SceneData* s, const SceneSyncState* ss);

#endif
