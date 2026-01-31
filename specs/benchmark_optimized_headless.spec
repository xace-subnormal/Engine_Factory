SOA Vector3 float x y z

CONFIG MAX_THREADS 8

UNIQUE World:
@@gravity float = 9.8f
@@plane_y float = 0.0f
@@delta_time float = 0.016f

GENERIC Cube count=3000000:
@@position Vector3 = {0.0f, 0.0f, 0.0f}
@@velocity Vector3 = {0.0f, 0.0f, 0.0f}
@@active bool = false
@@has_physics bool = false
@@color int = 0

SHARED Cube:
@@size Vector3 = {1.0f, 1.0f, 1.0f}
@@restitution float = 0.3f
@@mass float = 1.0f

SYSTEM ApplyPhysicsExtreme
PHASE LOOP
MODE PARALLEL

LOOP:
    HeadlessTimer
    AddCubesMassive
    ApplyPhysicsExtreme
    HeadlessStats
