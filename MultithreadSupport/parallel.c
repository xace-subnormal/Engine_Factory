

/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */


#include "parallel.h"
#include <pthread.h>
#include <stdint.h>

#ifndef GENERATED_MAX_THREADS
#define MAX_THREADS 8
#else
#define MAX_THREADS GENERATED_MAX_THREADS
#endif

typedef struct {
    void* world;
    SystemRangeFn fn;
    int start;
    int end;
} ThreadData;

static void* worker_static(void* arg) {
    ThreadData* data = (ThreadData*)arg;
    data->fn(data->world, data->start, data->end);
    return NULL;
}

void parallel_run(void* w, SystemRangeFn fn, int count) {
    if (count <= 1024) { 
        fn(w, 0, count);
        return;
    }

    pthread_t threads[MAX_THREADS];
    ThreadData thread_data[MAX_THREADS];

    int per_thread = count / MAX_THREADS;
    int remainder = count % MAX_THREADS;
    int current_start = 0;

    int threads_to_launch = 0;
    for (int i = 0; i < MAX_THREADS && current_start < count; i++) {
        thread_data[i].world = w;
        thread_data[i].fn = fn;
        thread_data[i].start = current_start;
        
        int chunk_size = per_thread + (i < remainder ? 1 : 0);
        thread_data[i].end = current_start + chunk_size;
        current_start = thread_data[i].end;

        if (pthread_create(&threads[i], NULL, worker_static, &thread_data[i]) == 0) {
            threads_to_launch++;
        } else {
            fn(w, thread_data[i].start, thread_data[i].end);
        }
    }

    for (int i = 0; i < threads_to_launch; i++) {
        pthread_join(threads[i], NULL);
    }
}
