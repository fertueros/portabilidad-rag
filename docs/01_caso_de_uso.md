# Caso de Uso: Automatización de Reportes de Portabilidad Móvil

## 1. Contexto y Antecedentes

La **Portabilidad Numérica Móvil (MNP)** es un derecho fundamental de los usuarios de servicios de telecomunicaciones que les permite conservar su número telefónico al cambiar de operador. En el Perú, este mecanismo, regulado por el **OSIPTEL** (Organismo Supervisor de Inversión Privada en Telecomunicaciones), es un indicador clave de la dinámica competitiva del mercado (OSIPTEL, 2024; ITU, 2018).

Mensualmente, OSIPTEL y diversos medios publican notas informativas sobre el desempeño de las operadoras (ganancias, pérdidas y saldo neto de líneas). Estas publicaciones son críticas para:
*   **Reguladores:** Monitorear la competencia y detectar prácticas desleales.
*   **Operadoras:** Ajustar estrategias comerciales y de retención (Cho & Park, 2014).
*   **Analistas y Prensa:** Informar a la opinión pública sobre las tendencias del mercado.

## 2. Definición del Problema

Actualmente, el monitoreo de estos indicadores se realiza a través de dashboards complejos y reportes manuales. Sin embargo, la literatura reciente advierte sobre problemas críticos en este enfoque tradicional:

### 2.1. Sobrecarga de Información y Cognitiva
La abundancia de datos en dashboards puede generar una **"sobrecarga de información"**, donde el volumen de inputs excede la capacidad de procesamiento del usuario (Arnold et al., 2023). Estudios recientes señalan que cuando el contenido de un dashboard es excesivo, se convierte en una barrera para la adopción de herramientas de Inteligencia de Negocios (BI), aumentando la carga cognitiva innecesariamente (Burnay et al., 2023; Ke et al., 2023).

### 2.2. Ineficiencia Operativa y Riesgo de Error
El análisis manual para extraer *insights* de estos dashboards requiere tiempo considerable de expertos. Además, la interpretación visual subjetiva puede llevar a errores, especialmente cuando la "alfabetización visual" de los usuarios varía (Liu et al., 2024).

### 2.3. Carencia de Narrativa Contextual
Los datos por sí solos no cuentan la historia completa. La falta de una narrativa que conecte los puntos (ej. *¿Por qué bajó Claro este mes vs el año pasado?*) limita la utilidad del reporte.

## 3. Propuesta de Solución

Este proyecto implementa un sistema automatizado **"End-to-End"** que integra Analítica de Datos (EDA) con Inteligencia Artificial Generativa (RAG + LLM) para producir **narrativas de datos automatizadas**.

### 3.1. Enfoque: Narrativas Automatizadas con GenAI
La solución se alinea con la tendencia emergente de usar GenAI para automatizar narrativas en dashboards de analítica, facilitando la comprensión de datos complejos sin intervención humana constante (Pinargote et al., 2024).

Esta tendencia ya es un estándar en la industria, adoptada por líderes como **Microsoft Power BI** con sus "Smart Narratives" (Microsoft, 2025) y **Amazon QuickSight** con "Autonarratives" (AWS, n.d.). Nuestra propuesta democratiza esta capacidad utilizando modelos abiertos y orquestación propia.

### 3.2. Arquitectura Híbrida: Determinismo + Creatividad
A diferencia de soluciones puramente generativas que pueden "alucinar" cifras, esta solución desacopla el cálculo de la redacción:
*   **Capa Determinística (EDA):** Python y Pandas calculan las cifras exactas. Estas son la "verdad base".
*   **Capa Generativa (LLM + RAG):** El modelo de lenguaje redacta la narrativa utilizando las cifras calculadas y consultando una base de conocimientos vectoriales para imitar el estilo histórico.

## 4. Impacto Esperado

*   **Reducción de Carga Cognitiva:** Entrega *insights* digeribles en lenguaje natural en lugar de tablas crudas.
*   **Eficiencia:** Automatización del 90% del flujo de trabajo de reporte.
*   **Confiabilidad:** 0% de desviación en cifras reportadas vs. fuentes oficiales.

## 5. Referencias y Literatura

**Académicas:**
1.  **Arnold, M., Goldschmitt, M., & Rigotti, T.** (2023). Dealing with information overload: A comprehensive review. *Frontiers in Psychology*, 14, 1122200. https://doi.org/10.3389/fpsyg.2023.1122200
2.  **Burnay, C., Bouraga, S., & Lega, M.** (2023). When dashboard’s content becomes a barrier: Exploring the effects of cognitive overloads on BI adoption. In *Research Challenges in Information Science* (pp. 435–451). Springer. https://doi.org/10.1007/978-3-031-33080-3_26
3.  **Cho, D., & Park, Y.** (2014). The effects of mobile number portability on market competition. *Telecommunications Policy*, 38(7), 673-684.
4.  **Ke, J., Liao, P., Li, J., & Luo, X.** (2023). Effect of information load and cognitive style on cognitive load of visualized dashboards for construction-related activities. *Automation in Construction*, 154, 105029. https://doi.org/10.1016/j.autcon.2023.105029
5.  **Lewis, P., et al.** (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. *NeurIPS 2020*.
6.  **Liu, Y., Pozdniakov, S., & Martinez-Maldonado, R.** (2024). The effects of visualisation literacy and data storytelling dashboards on teachers’ cognitive load. *Australasian Journal of Educational Technology*, 40(1), 78–93.
7.  **Pinargote, A., Calderón, E., Cevallos, K., Carrillo, G., Chiluiza, K., & Echeverria, V.** (2024). Automating data narratives in learning analytics dashboards using GenAI. *Joint Proceedings of LAK 2024 Workshops*. CEUR-WS.org.

**Industria:**
8.  **Amazon Web Services.** (n.d.). Insights that include autonarratives. *Amazon QuickSight User Guide*. Retrieved Jan 4, 2026.
9.  **Microsoft.** (2025). Creación de resúmenes de narración inteligente - Power BI. *Microsoft Learn*. https://learn.microsoft.com/es-es/power-bi/visuals/power-bi-visualization-smart-narrative
10. **OSIPTEL.** (2024). Portal de Información de Usuarios - Noticias de Portabilidad. https://www.osiptel.gob.pe
11. **ITU.** (2018). Mobile number portability. ITU-T Recommendations.
