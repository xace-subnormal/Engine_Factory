

/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */


#ifndef RENDER_PROTOCOL_H
#define RENDER_PROTOCOL_H

#include "graphics_types.h"
#include "scene_sync_state.h"

// Variables globales de escena gestionadas por el motor (GSPEC)
extern SceneData s;
extern SceneSyncState ss;

void backend_init(int width, int height, const char* title);
void backend_cleanup(void);
bool backend_should_close(void);

void backend_begin_frame(void);
void backend_end_frame(void);

void backend_update_gpu(uint32_t* vbo_id, const SceneData* s, const SceneSyncState* ss);
void backend_draw_instanced(void* model_ptr, const SceneData* s);

#endif
