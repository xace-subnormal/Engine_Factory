

/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */


#include <time.h>

void system_HeadlessTimer(World* w) {
    static clock_t last;
    static int first = 1;
    clock_t now = clock();
    
    if (first) {
        last = now;
        first = 0;
        w->world.delta_time = 0.016f;
        return;
    }
    
    float elapsed = (float)(now - last) / CLOCKS_PER_SEC;
    
    if (elapsed <= 0.0f) elapsed = 0.000001f;
    
    w->world.delta_time = elapsed;
    last = now;
}
