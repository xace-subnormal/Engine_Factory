

/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */


#include "scriptsupport.h"
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

static ScriptSupportState g_state = {0};

static int find_free_timer_slot(void) {
    for(int i=0;i<MAX_TIMERS;i++)
        if(!g_state.timers[i].active) return i;
    return -1;
}

static int find_timer_by_name(const char* name,uint32_t owner_id){
    for(int i=0;i<MAX_TIMERS;i++){
        if(g_state.timers[i].active &&
           strcmp(g_state.timers[i].name,name)==0 &&
           g_state.timers[i].owner_id==owner_id)
            return i;
    }
    return -1;
}

static void push_command(GameCommand cmd){
    if(g_state.command_count>=MAX_COMMANDS){
        scriptsupport_log("ERROR: Command buffer full");
        return;
    }
    g_state.commands[g_state.command_write_idx]=cmd;
    g_state.command_write_idx=(g_state.command_write_idx+1)%MAX_COMMANDS;
    g_state.command_count++;
}

static void push_event(GameEvent ev){
    if(g_state.event_count>=MAX_EVENTS){
        scriptsupport_log("ERROR: Event buffer full");
        return;
    }
    g_state.events[g_state.event_write_idx]=ev;
    g_state.event_write_idx=(g_state.event_write_idx+1)%MAX_EVENTS;
    g_state.event_count++;
}

void emit_spawn(uint16_t type,float x,float y,float z){GameCommand c={0};c.type=CMD_SPAWN;c.spawn.entity_type=type;c.spawn.x=x;c.spawn.y=y;c.spawn.z=z;push_command(c);}
void emit_destroy(uint32_t id){GameCommand c={0};c.type=CMD_DESTROY;c.target_id=id;push_command(c);}
void emit_set_position(uint32_t id,float x,float y,float z){GameCommand c={0};c.type=CMD_SET_POSITION;c.target_id=id;c.vec3_data.x=x;c.vec3_data.y=y;c.vec3_data.z=z;push_command(c);}
void emit_set_velocity(uint32_t id,float x,float y,float z){GameCommand c={0};c.type=CMD_SET_VELOCITY;c.target_id=id;c.vec3_data.x=x;c.vec3_data.y=y;c.vec3_data.z=z;push_command(c);}
void emit_set_health(uint32_t id,float h){GameCommand c={0};c.type=CMD_SET_HEALTH;c.target_id=id;c.float_data.health=h;push_command(c);}
void emit_start_timer(const char* n,float d,uint32_t owner){GameCommand c={0};c.type=CMD_START_TIMER;c.source_id=owner;strncpy(c.timer.timer_name,n,ENTITY_NAME_LEN-1);c.timer.duration=d;push_command(c);}
void emit_stop_timer(const char* n,uint32_t owner){GameCommand c={0};c.type=CMD_STOP_TIMER;c.source_id=owner;strncpy(c.timer.timer_name,n,ENTITY_NAME_LEN-1);push_command(c);}
void emit_event(EventType t,uint32_t src,uint32_t tgt,uint32_t d){GameCommand c={0};c.type=CMD_EMIT_EVENT;c.source_id=src;c.target_id=tgt;c.event.event_type=t;c.event.data=d;push_command(c);}
void emit_custom_event(const char* n,uint32_t src,uint32_t tgt,uint32_t d){GameCommand c={0};c.type=CMD_EMIT_EVENT;c.source_id=src;c.target_id=tgt;c.event.event_type=EVENT_CUSTOM;strncpy(c.event.custom_name,n,ENTITY_NAME_LEN-1);c.event.data=d;push_command(c);}

// Timers
bool is_timer_done(const char* name,uint32_t owner){int idx=find_timer_by_name(name,owner);return idx==-1?true:g_state.timers[idx].elapsed>=g_state.timers[idx].duration;}
float get_timer_elapsed(const char* name,uint32_t owner){int idx=find_timer_by_name(name,owner);return idx==-1?0.0f:g_state.timers[idx].elapsed;}

// API
void scriptsupport_clear_commands(void){g_state.command_write_idx=g_state.command_read_idx=g_state.command_count=0;}
int scriptsupport_get_command_count(void){return g_state.command_count;}
GameCommand* scriptsupport_get_command(int i){if(i<0||i>=g_state.command_count)return NULL;int idx=(g_state.command_read_idx+i)%MAX_COMMANDS;return &g_state.commands[idx];}
void scriptsupport_process_commands(void){scriptsupport_clear_commands();}

void scriptsupport_clear_events(void){g_state.event_write_idx=g_state.event_read_idx=g_state.event_count=0;}
int scriptsupport_get_event_count(void){return g_state.event_count;}
GameEvent* scriptsupport_get_event(int i){if(i<0||i>=g_state.event_count)return NULL;int idx=(g_state.event_read_idx+i)%MAX_EVENTS;return &g_state.events[idx];}
void scriptsupport_push_event(GameEvent e){push_event(e);}

void scriptsupport_update_timers(float dt){for(int i=0;i<MAX_TIMERS;i++){if(g_state.timers[i].active){g_state.timers[i].elapsed+=dt;if(g_state.timers[i].elapsed>=g_state.timers[i].duration){GameEvent ev={0};ev.type=EVENT_CUSTOM;ev.source_id=g_state.timers[i].owner_id;snprintf(ev.custom_name,ENTITY_NAME_LEN,"timer_%s_done",g_state.timers[i].name);push_event(ev);g_state.timers[i].active=false;}}}}
int scriptsupport_get_timer_count(void){return g_state.timer_count;}
ScriptTimer* scriptsupport_get_timer(int i){return (i<0||i>=g_state.timer_count)?NULL:&g_state.timers[i];}

void scriptsupport_register_entity_type(const char* n,uint16_t id,uint32_t max){if(g_state.entity_type_count>=32){scriptsupport_log("ERROR: Too many entity types");return;}EntityTypeInfo* e=&g_state.entity_types[g_state.entity_type_count++];strncpy(e->name,n,ENTITY_NAME_LEN-1);e->type_id=id;e->max_count=max;}
EntityTypeInfo* scriptsupport_get_entity_type(uint16_t id){for(int i=0;i<g_state.entity_type_count;i++)if(g_state.entity_types[i].type_id==id)return &g_state.entity_types[i];return NULL;}

void scriptsupport_log(const char* f,...){if(g_state.log_count>=MAX_LOG_ENTRIES)return;va_list args;va_start(args,f);char* buf=g_state.log_entries[g_state.log_write_idx];vsnprintf(buf,256,f,args);va_end(args);g_state.log_write_idx=(g_state.log_write_idx+1)%MAX_LOG_ENTRIES;g_state.log_count=(g_state.log_count+1)%MAX_LOG_ENTRIES;}
int scriptsupport_get_log_count(void){return g_state.log_count;}
const char* scriptsupport_get_log_entry(int i){if(i<0||i>=g_state.log_count)return NULL;int start=(g_state.log_write_idx-g_state.log_count+MAX_LOG_ENTRIES)%MAX_LOG_ENTRIES;return g_state.log_entries[(start+i)%MAX_LOG_ENTRIES];}

ScriptSupportState* scriptsupport_get_state(void){return &g_state;}
void scriptsupport_reset(void){memset(&g_state,0,sizeof(g_state));}
