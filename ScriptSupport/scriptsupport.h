

/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */


#ifndef SCRIPTSUPPORT_H
#define SCRIPTSUPPORT_H

#include <stdint.h>
#include <stdbool.h>
#include <string.h>

#define MAX_COMMANDS 128
#define MAX_EVENTS 64
#define MAX_TIMERS 32
#define MAX_LOG_ENTRIES 256
#define ENTITY_NAME_LEN 32

typedef enum {
    CMD_SPAWN,
    CMD_DESTROY,
    CMD_SET_POSITION,
    CMD_SET_VELOCITY,
    CMD_SET_HEALTH,
    CMD_START_TIMER,
    CMD_STOP_TIMER,
    CMD_EMIT_EVENT
} CommandType;

typedef enum {
    EVENT_TICK,
    EVENT_DEATH,
    EVENT_HIT,
    EVENT_SPAWN,
    EVENT_COLLISION,
    EVENT_INPUT,
    EVENT_DAMAGE,
    EVENT_HEAL,
    EVENT_CUSTOM
} EventType;

typedef struct {
    char name[ENTITY_NAME_LEN];
    uint16_t type_id;
    uint32_t max_count;
} EntityTypeInfo;

typedef struct {
    CommandType type;
    uint32_t source_id;
    uint32_t target_id;
    union {
        struct { uint16_t entity_type; float x,y,z; } spawn;
        struct { uint32_t entity_id; } destroy;
        struct { float x,y,z; } vec3_data;
        struct { float health; } float_data;
        struct { char timer_name[ENTITY_NAME_LEN]; float duration; } timer;
        struct { EventType event_type; char custom_name[ENTITY_NAME_LEN]; uint32_t data; } event;
    };
} GameCommand;

typedef struct {
    EventType type;
    uint32_t source_id;
    uint32_t target_id;
    uint32_t data;
    float timestamp;
    char custom_name[ENTITY_NAME_LEN];
} GameEvent;

typedef struct {
    char name[ENTITY_NAME_LEN];
    float duration;
    float elapsed;
    bool active;
    uint32_t owner_id;
} ScriptTimer;

// Estado visible para scripts
typedef struct {
    int entity_count;
    uint32_t entity_ids[MAX_COMMANDS];
    float positions[MAX_COMMANDS][3]; // x,y,z
    float velocities[MAX_COMMANDS][3];
    float healths[MAX_COMMANDS];
    bool collisions[MAX_COMMANDS][MAX_COMMANDS]; // precomputado por motor
} ScriptStateView;

void emit_spawn(uint16_t type, float x, float y, float z);
void emit_destroy(uint32_t entity_id);
void emit_set_position(uint32_t entity_id, float x, float y, float z);
void emit_set_velocity(uint32_t entity_id, float x, float y, float z);
void emit_set_health(uint32_t entity_id, float health);
void emit_start_timer(const char* name, float duration, uint32_t owner_id);
void emit_stop_timer(const char* name, uint32_t owner_id);
void emit_event(EventType type, uint32_t source_id, uint32_t target_id, uint32_t data);
void emit_custom_event(const char* name, uint32_t source_id, uint32_t target_id, uint32_t data);

void scriptsupport_clear_commands(void);
int scriptsupport_get_command_count(void);
GameCommand* scriptsupport_get_command(int index);
void scriptsupport_process_commands(void);

void scriptsupport_clear_events(void);
int scriptsupport_get_event_count(void);
GameEvent* scriptsupport_get_event(int index);
void scriptsupport_push_event(GameEvent event);

void scriptsupport_update_timers(float dt);
int scriptsupport_get_timer_count(void);
ScriptTimer* scriptsupport_get_timer(int index);

void scriptsupport_register_entity_type(const char* name, uint16_t type_id, uint32_t max_count);
EntityTypeInfo* scriptsupport_get_entity_type(uint16_t type_id);

void scriptsupport_log(const char* format, ...);
int scriptsupport_get_log_count(void);
const char* scriptsupport_get_log_entry(int index);

typedef struct {
    GameCommand commands[MAX_COMMANDS];
    GameEvent events[MAX_EVENTS];
    ScriptTimer timers[MAX_TIMERS];
    char log_entries[MAX_LOG_ENTRIES][256];
    int command_write_idx, command_read_idx, command_count;
    int event_write_idx, event_read_idx, event_count;
    int timer_count, log_write_idx, log_count;
    EntityTypeInfo entity_types[32];
    int entity_type_count;
    ScriptStateView view;
} ScriptSupportState;

ScriptSupportState* scriptsupport_get_state(void);
void scriptsupport_reset(void);

#endif
