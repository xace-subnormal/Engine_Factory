

/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */


#include <stdio.h>
#include <stdlib.h>

void system_HeadlessStats(World* w) {
    if (w->frame % 100 == 0) {
        printf("[HEADLESS] Frame: %lu | Activos: %d | Delta: %.5f s\n", 
               w->frame, w->cube._active, w->world.delta_time);
        fflush(stdout);
    }
    
    if (w->cube._active >= 3000000) {
        printf("\nBENCHMARK COMPLETADO: 3,000,000 de cubos procesados\n");
        fflush(stdout);
        w->running = false; // Finalizar el benchmark automáticamente
    }
}

