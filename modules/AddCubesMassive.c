

/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */


// REQ: Cube.position as pos
// REQ: Cube.velocity as vel
// REQ: Cube.active as act
// REQ: Cube._active as count
// REQ: Cube.has_physics as phys
// REQ: Cube.color as col

#include <stdint.h>
#include <stdbool.h>

void system_AddCubesMassive(float* pos_x, float* pos_y, float* pos_z,
                             float* vel_x, float* vel_y, float* vel_z, 
                             bool* act, int32_t* count, bool* phys, int* col) {
    int to_add = 256;
    int max = 3000000;
    
    int palette[] = { 0xFF0000, 0x00FF00, 0x0000FF, 0xFFFF00, 0xFF00FF };

    for (int k = 0; k < to_add && *count < max; k++) {
        int i = *count;
        
        pos_x[i] = (float)((i % 2000) - 1000) * 1.5f;
        pos_y[i] = 1000.0f + (float)(i / 2000) * 0.5f;
        pos_z[i] = (float)(((i / 2000) % 1500) - 750) * 1.5f;
        
        vel_y[i] = 0.0f;
        act[i] = true;
        phys[i] = true;
        col[i] = palette[i % 5];
        
        (*count)++;
    }
}
