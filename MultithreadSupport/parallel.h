

/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */


#ifndef PARALLEL_H
#define PARALLEL_H

#include <pthread.h>
#include <stdlib.h>

// Tipo para funciones de rango (para sistemas paralelos)
typedef void (*SystemRangeFn)(void* world, int start, int end);

// Prototipo para ejecución paralela pasiva
void parallel_run(void* world, SystemRangeFn func, int total_items);

#endif
