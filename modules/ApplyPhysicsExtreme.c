

/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */


#include <math.h>

void system_ApplyPhysicsExtreme_range(World* w, int start, int end) {
    float g = w->world.gravity;
    float dt = w->world.delta_time;
    
    if (end > w->cube._active) end = w->cube._active;

    for (int i = start; i < end; i++) {
        if (w->cube.has_physics[i]) {
            w->cube.velocity_y[i] -= g * dt;
            w->cube.position_y[i] += w->cube.velocity_y[i] * dt;
            
            if (w->cube.position_y[i] < 0.0f) {
                w->cube.position_y[i] = 0.0f;
                w->cube.velocity_y[i] *= -0.2f;
            }
        }
    }
}
