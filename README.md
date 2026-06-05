<div align="center">
  <h1>🤖 JellyInspector AI Skill</h1>
  <p><b>El agente IA definitivo para la auditoría y corrección extrema de metadatos en Jellyfin</b></p>
  
  <p>
    <a href="https://github.com/jellyfin/jellyfin"><img src="https://img.shields.io/badge/Jellyfin-10.8%2B-00A4DC?style=for-the-badge&logo=jellyfin&logoColor=white" alt="Jellyfin" /></a>
    <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.10%2B-FFD43B?style=for-the-badge&logo=python&logoColor=blue" alt="Python" /></a>
    <a href="https://myanimelist.net"><img src="https://img.shields.io/badge/API-Jikan_&_AniList-2E51A2?style=for-the-badge&logo=myanimelist&logoColor=white" alt="APIs" /></a>
    <a href="#"><img src="https://img.shields.io/badge/Status-Production_Ready-success?style=for-the-badge" alt="Status" /></a>
  </p>
</div>

---

## 🚀 ¿Qué es JellyInspector?

**JellyInspector** no es solo un conjunto de scripts; es una **Skill para Agentes de IA autónomos**.

Está diseñado para que una IA se conecte a tu servidor Jellyfin, audite tu biblioteca entera y repare el caos estructural que los scrapers tradicionales (como TMDB o AniDB) causan en las series complejas. La IA se encarga de inyectar datos puros desde las APIs de **MyAnimeList (Jikan)** y **AniList**, blindando los metadatos para que nunca vuelvan a romperse.

### 🔥 ¿Qué problemas soluciona tu Agente IA?

- 🏷️ **Nombres Genéricos**: Evita que los plugins agrupen todo bajo "Season 1", "Season 2", restaurando los nombres reales de los arcos narrativos.
- 👻 **Temporadas Fantasma**: Detecta y fusiona duplicados visuales causados por desajustes entre las carpetas físicas y las temporadas virtuales de los plugins.
- 🔄 **Drift de Scrapers**: Blinda cada cambio usando `LockedFields` nativos. Ningún scraper revertirá el trabajo de la IA.
- 📝 **Episodios Vacíos**: Inyecta títulos customizados y sinopsis desde bases de datos externas cuando Jellyfin falla.
- 🏴‍☠️ **Metadatos Contaminados**: Limpia etiquetas basura inyectadas en campos invisibles (como el `OriginalTitle`) que arruinan la organización.

---

## 🧠 Activación de la IA (AI Usage)

JellyInspector está construido pensando en **Agentes LLM** (como Claude, GPT-4o, o el sistema Antigravity). Para que tu IA haga el trabajo sucio por ti, solo necesitas darle el contexto de la Skill.

### 1. Preparar el entorno

Clona el repo y configura tus credenciales para que la IA tenga acceso:

```bash
git clone https://github.com/manumyx/jellyinspector
cd jellyinspector
pip install -r requirements.txt
cp .env.example .env
```

_(Edita el `.env` con tu URL y API Key de Jellyfin)_

### 2. Invocar a la IA

Proporciona a tu Agente IA acceso al directorio del proyecto y dile que lea el **Documento de Activación**:

> _"Agente, lee las instrucciones en `docs/SKILL.md`. Asume el rol de JellyInspector y audita mi catálogo entero."_

### 3. El Protocolo de la IA

Una vez activado, el agente operará bajo un estricto protocolo de producción definido en [`docs/SKILL.md`](docs/SKILL.md):

1. **Auditoría masiva** de tu catálogo usando `agent_catalog_scan.py`.
2. Lanzamiento de **subagentes paralelos** para aislar cada serie problemática.
3. Creación de **Data Mappings** automáticos consultando APIs.
4. Ejecución del **Anti-Drift Final Check**: La IA tiene prohibido terminar la tarea hasta que el auditor reporte `0 issues`.

---

## 🛠️ Estructura de la Skill

La arquitectura separa las herramientas de ejecución (para la IA/humano), los datos (mappings), y la lógica de activación (docs).

```text
jellyinspector/
├── docs/                            # 🧠 El "Cerebro" de la IA
│   ├── SKILL.md                     # Prompt de Activación Maestro (Reglas de la IA)
│   ├── jellyfin_api_reference.md    # Conocimiento de bugs empíricos de la API
│   └── external_apis_reference.md   # Conocimiento sobre Jikan/AniList/TMDB
├── tools/                           # ⚙️ Herramientas de Ejecución
│   ├── agent_catalog_scan.py        # Escaneo de alto nivel del servidor
│   ├── agent_auditor.py             # Auditoría profunda (Exit Code 0/1)
│   ├── agent_universal_fixer.py     # Corrector de Temporadas
│   ├── agent_jikan_episodes.py      # Inyector de Episodios
│   ├── agent_ghost_merger.py        # Fusionador de temporadas fantasma
│   ├── jellyfin_api.py              # Cliente REST reforzado
│   └── agent_refresh.py             # Trigger de escaneo Jellyfin
└── mappings/                        # 🗃️ Base de Datos Local
    ├── example_seasons.json.template
    └── example_episodes.json.template
```

---

## 💻 Uso Manual (Modo Humano)

Si prefieres no usar una IA y quieres lanzar los scripts de forma manual, las herramientas están diseñadas para ser modulares y tolerantes a fallos (incrementales).

### 1. Auditar una serie

Te dirá exactamente qué episodios no tienen título, sinopsis, o si hay temporadas fantasma:

```bash
cd tools
python agent_auditor.py --series_id <JELLYFIN_SERIES_ID>
```

### 2. Corregir Temporadas

Crea un JSON copiando el template `mappings/example_seasons.json.template` y ejecuta:

```bash
python agent_universal_fixer.py \
    --series_id <ID> \
    --mapping ../mappings/mi_serie_seasons.json
```

### 3. Inyectar Metadatos de Episodios (Jikan/MAL)

Crea un JSON desde el template `mappings/example_episodes.json.template` y ejecuta:

```bash
python agent_jikan_episodes.py \
    --series_id <ID> \
    --mapping ../mappings/mi_serie_episodes.json
```

> 💡 _Nota: Si la API de Jikan te da rate limit (error 429), simplemente vuelve a ejecutar el script. Es incremental y saltará lo que ya esté arreglado._

### 4. Fusionar Temporadas Fantasma

```bash
python agent_ghost_merger.py --series_id <ID>
```

### 5. Refrescar la Biblioteca

Fuerza a Jellyfin a leer la base de datos para reflejar todos los cambios en la UI:

```bash
python agent_refresh.py
```

---

> Made with ☕ by [manumyx](https://github.com/manumyx)
