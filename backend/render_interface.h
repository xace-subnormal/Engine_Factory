

/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */


#ifndef RENDER_INTERFACE_H
#define RENDER_INTERFACE_H

#include <stdint.h>
#include <stdbool.h>
#include "../modules/graphics_types.h"

// El contrato que todo backend debe implementar
typedef struct {
    void (*init)(int width, int height, const char* title);
    void (*begin_drawing)();
    void (*end_drawing)();
    void (*update_gpu)(uint32_t* vbo_id, const SceneData* s, const SceneSyncState* ss);
    void (*draw_instanced)(Model model, const SceneData* s);
    void (*cleanup)();
    bool (*should_close)();
} RenderBackend;

#endif
