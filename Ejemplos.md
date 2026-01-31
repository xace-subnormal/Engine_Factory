# Ejemplos Destacados

### 1. Benchmark de Estabilidad 3M (`specs/benchmark_optimized_headless.spec`)
Prueba de estrés diseñada para medir el rendimiento puro del motor procesando 3,000,000 de entidades que se activan gradualmente.

*   **Características**: 
    *   Modo *headless* (sin ventana gráfica) para medición pura de lógica.
    *   Simulación física masiva paralelizada (multihilo).
    *   Arquitectura optimizada para caché (SoA).
*   **Construcción**:
    ```bash
    python3 builder.py specs/benchmark_optimized_headless.spec
    gcc main.c MultithreadSupport/parallel.c -o benchmark_optimized -lm -lpthread -O2 -march=native
    ```

---

## Nota sobre Rendimiento Nativo
Para obtener los mejores resultados en los benchmarks masivos, utiliza siempre los flags de arquitectura nativa:
`-march=native -mtune=native`
O algún flag de optimización:
`-O2` u `-O3`

Pero ten en cuenta que usar `-march=native -mtune=native` implica que al compilar, el binario resultante va a funcionar usando optimizaciones específicas de tu procesador, lo que implica que no va a funcionar en procesadores diferentes a menos que sea el mismo modelo exacto.
