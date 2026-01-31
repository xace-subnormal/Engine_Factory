

/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */


#include "backend_raylib.h"
#include "rlgl.h"
#include "raymath.h"

static uint32_t gpu_vbo_capacity = 0;

void backend_raylib_draw_instanced(Model model, const SceneData* s) {
    if (s == NULL || s->count == 0) return;

    Mesh mesh = model.meshes[0];
    Material material = model.materials[0];

    // Sincronizar la matriz de vista-proyección del shader
    // Esto es para que las instancias se dibujen en el lugar correcto
    Matrix matView = rlGetMatrixModelview();
    Matrix matProj = rlGetMatrixProjection();
    Matrix matViewProj = MatrixMultiply(matView, matProj);
    
    int mvpLoc = GetShaderLocation(material.shader, "mvp");
    if (mvpLoc != -1) SetShaderValueMatrix(material.shader, mvpLoc, matViewProj);

    rlEnableShader(material.shader.id);
        
        rlEnableVertexArray(mesh.vaoId);
            
            rlDrawVertexArrayInstanced(0, mesh.vertexCount, s->count);
            
        rlDisableVertexArray();
        
    rlDisableShader();
}

void backend_raylib_update_gpu(unsigned int* vbo_id_ptr, const SceneData* s, const SceneSyncState* ss) {
    if (s == NULL) return;

    if (s->count > gpu_vbo_capacity) {
        if (*vbo_id_ptr != 0) rlUnloadVertexBuffer(*vbo_id_ptr);
        uint32_t new_capacity = s->capacity;
        *vbo_id_ptr = rlLoadVertexBuffer(s->instances, new_capacity * sizeof(RenderInstance), true);
        gpu_vbo_capacity = new_capacity;
        return;
    }

    if (!ss->dirty) return;
    
    uint32_t offset = ss->dirty_min * sizeof(RenderInstance);
    uint32_t size = (ss->dirty_max - ss->dirty_min + 1) * sizeof(RenderInstance);
    
    if (offset + size > gpu_vbo_capacity * sizeof(RenderInstance)) return;
    
    rlUpdateVertexBuffer(*vbo_id_ptr, &s->instances[ss->dirty_min], size, offset);
}
