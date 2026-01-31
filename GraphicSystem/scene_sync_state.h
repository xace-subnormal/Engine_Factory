

/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */


#ifndef SCENE_SYNC_STATE_H
#define SCENE_SYNC_STATE_H

#include "graphics_types.h"
#include <stdlib.h>
#include <string.h>

typedef struct {
    bool dirty;
    uint32_t dirty_min;
    uint32_t dirty_max;
} SceneSyncState;

static inline void scene_sync_reset(SceneSyncState* ss) {
    ss->dirty = false;
    ss->dirty_min = 0xFFFFFFFF;
    ss->dirty_max = 0;
}

static inline void scene_sync_mark(SceneSyncState* ss, uint32_t index) {
    ss->dirty = true;
    if (index < ss->dirty_min) ss->dirty_min = index;
    if (index > ss->dirty_max) ss->dirty_max = index;
}

// Funciones de gestión del SceneData
static inline void scene_init(SceneData* s, uint32_t initial_capacity) {
    if (initial_capacity == 0) initial_capacity = 1;
    s->instances = (RenderInstance*)malloc(initial_capacity * sizeof(RenderInstance));
    if (s->instances == NULL) return;
    s->count = 0;
    s->capacity = initial_capacity;
    memset(s->instances, 0, initial_capacity * sizeof(RenderInstance));
}

static inline void scene_free(SceneData* s) {
    if (s->instances) free(s->instances);
    s->count = 0; s->capacity = 0;
}

static inline void scene_ensure_capacity(SceneData* s, uint32_t required_capacity) {
    if (s->capacity >= required_capacity) return;
    uint32_t new_capacity = s->capacity;
    if (new_capacity == 0) new_capacity = 1;
    while (new_capacity < required_capacity) new_capacity *= 2;
    RenderInstance* new_instances = (RenderInstance*)realloc(s->instances, new_capacity * sizeof(RenderInstance));
    if (new_instances) { s->instances = new_instances; s->capacity = new_capacity; }
}

#endif
