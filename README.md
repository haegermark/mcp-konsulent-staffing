# MCP Konsulent-Staffing Løsning

En **Model Context Protocol (MCP)** løsning for å finne tilgjengelige konsulenter basert på ferdigheter og kapasitet. Denne løsningen demonstrerer ekte MCP-arkitektur der en klient-tjeneste kobler til en MCP server for å hente strukturert data og bruker LLM til å generere menneskeleselige sammendrag.

## Hva er MCP (Model Context Protocol)?

MCP er Anthropic's åpne standard for å koble AI-systemer til eksterne datakilder og verktøy. Det fungerer som "USB-C for AI" - en standardisert protokoll som gjør det enkelt for AI-assistenter å:
- Hente data fra eksterne systemer via JSON-RPC over stdio
- Kalle verktøy og funksjoner
- Få tilgang til ressurser på en sikker måte

## Arkitektur

Denne løsningen består av to komponenter basert på MCP-protokollen:

### 1. MCP Server: konsulent-api
**Funksjon**: Eksponerer konsulent-data som MCP-verktøy (tools)

**MCP Tool**:
- `hent_konsulenter()` - Returnerer alle konsulenter som JSON

**Data struktur**:
```json
{
  "id": 1,
  "navn": "Fredrik",
  "ferdigheter": ["python", "fastapi", "docker"],
  "belastning_prosent": 50
}
```

**Port**: Kjører som subprocess (ingen HTTP port)

### 2. MCP Client + REST API: llm-verktøy-api
**Funksjon**:
- Kobler til MCP server via stdio-transport (spawner subprocess)
- Kaller MCP-verktøy `hent_konsulenter()` for å hente data
- Filtrerer data basert på tilgjengelighet og ferdigheter
- Bruker LLM (GPT-4o-mini) til å generere menneskeleselige sammendrag på norsk
- Eksponerer REST API for ekstern bruk

**REST Endepunkter**:
- `GET /tilgjengelige-konsulenter/sammendrag` - Hovedendepunkt (se eksempler under)
- `GET /health` - Health check

**Port**: 4000 (host) → 4000 (container)

## Ports og URL-er

| Tjeneste | Container Port | Host Port | URL |
|----------|---------------|-----------|-----|
| llm-verktøy-api | 4000 | 4000 | http://localhost:4000 |
| konsulent-api (MCP) | - | - | Subprocess via stdio |

**Viktige URL-er**:
- API Hovedendepunkt: `http://localhost:4000/tilgjengelige-konsulenter/sammendrag`
- API Dokumentasjon (Swagger): `http://localhost:4000/docs`
- Health Check: `http://localhost:4000/health`

## Hvorfor MCP vs Vanlig REST API?

| Aspekt | Tradisjonell REST API | MCP Løsning |
|--------|----------------------|-------------|
| **Kommunikasjon** | HTTP requests | MCP protokoll (JSON-RPC) via stdio |
| **Schema** | Må håndteres manuelt | Automatisk generert fra type hints |
| **Discovery** | Manuell dokumentasjon | Innebygd tool discovery |
| **Sikkerhet** | Token-basert auth | Process-level isolation |
| **AI-integrasjon** | Custom parsing | Native support i Claude Desktop og lignende |
| **Standardisering** | Hver API er unik | Felles protokoll på tvers av systemer |

## LLM Modellvalg: GPT-4o-mini

### Begrunnelse
Jeg har valgt **OpenAI GPT-4o-mini** (`openai/gpt-4o-mini`) av følgende grunner:

1. **Norsk språkstøtte**: GPT-4o-mini har utmerket støtte for norsk språk og kan generere naturlige, grammatisk korrekte norske sammendrag.

2. **Kostnadseffektivitet**:
   - Input: $0.15 per million tokens
   - Output: $0.60 per million tokens
   - Betydelig billigere enn GPT-4 Turbo og Claude 3.5 Sonnet
   - Med 300 max tokens per sammendrag kan vi generere mange tusen sammendrag for $5 credit

3. **Responstid**: Rask og effektiv (typisk <2s)

4. **Instruksjonsetterfølgelse**: God til å følge spesifikke instruksjoner om format og struktur

5. **OpenAI SDK**: Ren integrasjon via offisiell OpenAI SDK (som også fungerer med OpenRouter)

### Alternative modeller vurdert
- **GPT-4 Turbo**: Dyrere ($10/$30 per million tokens), bedre kvalitet men overkill for sammendrag
- **Claude 3.5 Sonnet**: Dyrere ($3/$15 per million tokens), utmerket kvalitet men høyere kostnad
- **Claude 3 Haiku**: Billigere, men svakere tekstgenerering enn GPT-4o-mini

## Forutsetninger

- Docker og Docker Compose installert
- Port 4000 tilgjengelig
- OpenRouter API-nøkkel (settes i .env-filen)

## Installasjon og Kjøring

### 1. Klon eller naviger til prosjektet
```bash
cd mcp_interview
```

### 2. Opprett .env-fil med din OpenRouter API-nøkkel
Opprett filen `.env` i root-katalogen:
```
OPENROUTER_API_KEY=din-api-nøkkel-her
```

> **OBS**: `.env` er i `.gitignore` og commites ikke til Git av sikkerhetsmessige årsaker.

### 3. Bygg og start løsningen
```bash
docker compose up --build -d
```

Dette vil:
- Bygge llm-verktoy-api image
- Mount konsulent-api/server.py som volume
- Starte llm-verktoy-api på port 4000
- Klienten vil starte MCP serveren som en subprocess via stdio

### 4. Verifiser at tjenesten kjører
```bash
# Test health
curl http://localhost:4000/health

# Test med Docker
docker ps
```

Forventet output:
```json
{"status": "ok", "type": "MCP Client"}
```

## Bruk av API-et

### Query Parametere

**min_tilgjengelighet_prosent** (påkrevd):
- Type: Integer (0-100)
- Beskrivelse: Minimum tilgjengelighet i prosent
- Beregning: `tilgjengelighet = 100 - belastning_prosent`

**påkrevd_ferdighet** (valgfri):
- Type: String
- Beskrivelse: Ferdighet(er) som konsulenten må ha
- Format: Enkelt: `"python"`, Flere: `"python,docker"`
- Logikk: Konsulenten må ha ALLE spesifiserte ferdigheter (AND-logikk)

### Eksempel 1: Finn konsulenter med minst 50% tilgjengelighet og Python

**Request**:
```bash
curl "http://localhost:4000/tilgjengelige-konsulenter/sammendrag?min_tilgjengelighet_prosent=50&påkrevd_ferdighet=python"
```

**Forventet respons**:
```json
{
  "sammendrag": "Det ble funnet 2 konsulenter som oppfyller kriteriene om minimum 50% tilgjengelighet og ferdigheten python. Konsulentene er Fredrik med 50% tilgjengelighet, og Elias med 60% tilgjengelighet."
}
```

### Eksempel 2: Flere ferdigheter (AND-logikk)

**Request**:
```bash
curl "http://localhost:4000/tilgjengelige-konsulenter/sammendrag?min_tilgjengelighet_prosent=40&påkrevd_ferdighet=python,docker"
```

Konsulenten må ha BÅDE python OG docker.

**Forventet respons**:
```json
{
  "sammendrag": "Det ble funnet 1 konsulent som oppfyller søkekriteriene med minimum 40% tilgjengelighet og ferdighetene python og docker. Konsulenten er Fredrik, som har 50% tilgjengelighet."
}
```

### Eksempel 3: Ingen match

**Request**:
```bash
curl "http://localhost:4000/tilgjengelige-konsulenter/sammendrag?min_tilgjengelighet_prosent=60&påkrevd_ferdighet=golang"
```

**Forventet respons**:
```json
{
  "sammendrag": "Ingen konsulenter ble funnet som oppfylte kriteriene om minimum 60% tilgjengelighet og ferdigheten golang."
}
```

### Eksempel 4: Kun tilgjengelighet (ingen ferdighet)

**Request**:
```bash
curl "http://localhost:4000/tilgjengelige-konsulenter/sammendrag?min_tilgjengelighet_prosent=30"
```

Finner alle konsulenter med minst 30% tilgjengelighet, uavhengig av ferdigheter.

### Interaktiv API Dokumentasjon

Åpne i nettleser for Swagger UI:
```
http://localhost:4000/docs
```

Her kan du:
- Se alle tilgjengelige endepunkter
- Prøve ut requests med visuelt grensesnitt
- Se request/response schemas

## Prosjektstruktur

```
mcp_interview/
├── konsulent-api/           # MCP Server
│   ├── server.py           # FastMCP server med tool
│   └── requirements.txt    # mcp>=1.2.0
├── llm-verktoy-api/        # MCP Client + REST API
│   ├── Dockerfile
│   ├── client.py           # MCP klient + FastAPI + LLM
│   └── requirements.txt    # mcp, fastapi, uvicorn, openai
├── docker-compose.yml      # Port 4000:4000
├── .env                    # OPENROUTER_API_KEY (ikke i Git)
├── .gitignore
└── README.md
```

## MCP Flow Diagram

```
┌─────────────────┐
│   User/Browser  │
└────────┬────────┘
         │ HTTP GET Request
         │ http://localhost:4000/tilgjengelige-konsulenter/sammendrag
         ▼
┌─────────────────────────────────────────────────────────┐
│  Docker Container: llm-verktoy-api (Port 4000)          │
│                                                           │
│  ┌────────────────────────────────────────────────────┐  │
│  │  FastAPI REST API (client.py)                      │  │
│  │  - Mottar HTTP request                             │  │
│  │  - Parser query params                             │  │
│  └──────────────────┬─────────────────────────────────┘  │
│                     │                                     │
│                     ▼                                     │
│  ┌────────────────────────────────────────────────────┐  │
│  │  MCP Client (stdio transport)                      │  │
│  │  - Spawner subprocess: python server.py            │  │
│  │  - Kaller MCP tool: hent_konsulenter()             │  │
│  └──────────────────┬─────────────────────────────────┘  │
│                     │                                     │
│                     │ JSON-RPC via stdio                  │
│                     ▼                                     │
│  ┌────────────────────────────────────────────────────┐  │
│  │  MCP Server (subprocess)                           │  │
│  │  server.py - FastMCP                               │  │
│  │  - Tool: hent_konsulenter()                        │  │
│  │  - Returns: JSON list av konsulenter               │  │
│  └──────────────────┬─────────────────────────────────┘  │
│                     │                                     │
│                     │ JSON data                           │
│                     ▼                                     │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Data Filtering (filter_konsulenter)              │  │
│  │  - Beregn tilgjengelighet: 100 - belastning       │  │
│  │  - Filtrer på min_tilgjengelighet_prosent          │  │
│  │  - Filtrer på påkrevd_ferdighet (AND-logikk)      │  │
│  └──────────────────┬─────────────────────────────────┘  │
│                     │                                     │
│                     │ Filtrerte konsulenter               │
│                     ▼                                     │
│  ┌────────────────────────────────────────────────────┐  │
│  │  LLM Integration (generer_sammendrag_med_llm)     │  │
│  │  - OpenAI SDK → OpenRouter                         │  │
│  │  - Model: openai/gpt-4o-mini                       │  │
│  │  - Temperature: 0.7                                │  │
│  │  - Max tokens: 300                                 │  │
│  │  - Prompt: System + User (norsk sammendrag)       │  │
│  └──────────────────┬─────────────────────────────────┘  │
│                     │                                     │
│                     │ LLM-generert sammendrag             │
│                     ▼                                     │
│  ┌────────────────────────────────────────────────────┐  │
│  │  HTTP Response                                     │  │
│  │  {"sammendrag": "...norsk tekst..."}               │  │
│  └────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Docker Commands

### Start tjenesten
```bash
docker compose up -d
```

### Start med rebuild
```bash
docker compose up --build -d
```

### Stopp tjenesten
```bash
docker compose down
```

### Se logs
```bash
docker logs llm-verktoy-api

# Follow logs
docker logs llm-verktoy-api --follow

# Last 50 lines
docker logs llm-verktoy-api --tail 50
```

### Se kjørende containere
```bash
docker ps
```

### Restart container
```bash
docker compose restart
```

## Konsulentdata

Systemet inneholder følgende hardkodede konsulenter (i `konsulent-api/server.py`):

| ID | Navn | Ferdigheter | Belastning | Tilgjengelighet |
|----|------|-------------|------------|-----------------|
| 1 | Fredrik | python, fastapi, docker | 50% | 50% |
| 2 | Elias | artificial intelligence, data-science, software engineering, matlab, mysql, java, python | 40% | 60% |
| 3 | Daniel | artificial intelligence, data-science, software engineering, machine learning, fastapi, django, pandas, next.js, postgresql, python, java, sql, javascript | 80% | 20% |
| 4 | Erlend | artificial intelligence, data-science, software engineering, c++, python | 60% | 40% |
| 5 | Adrian | artificial intelligence, data-science, software engineering, python, golang, kubernetes, docker | 70% | 30% |

**Tilgjengelighet beregnes som**: `100 - belastning_prosent`

## Feilsøking

### Problem: Port 4000 allerede i bruk
```bash
# Windows - finn hvilken prosess bruker port 4000:
netstat -ano | findstr :4000

# Stopp Docker container:
docker compose down

# Eller endre port i docker-compose.yml til f.eks. 3000:4000
```

### Problem: Container starter ikke
```bash
# Sjekk logs for feilmeldinger:
docker logs llm-verktoy-api

# Sjekk at .env filen eksisterer og har OPENROUTER_API_KEY
cat .env

# Rebuild fra scratch:
docker compose down
docker compose up --build
```

### Problem: MCP connection timeout
```bash
# Sjekk at server.py er mounted korrekt:
docker exec llm-verktoy-api ls -la /mcp-server/

# Sjekk at mcp pakken er installert:
docker exec llm-verktoy-api pip list | grep mcp

# Se detaljerte logs:
docker logs llm-verktoy-api --tail 100
```

### Problem: LLM returnerer ikke sammendrag
```bash
# Sjekk at OPENROUTER_API_KEY er satt:
docker exec llm-verktoy-api printenv | grep OPENROUTER

# Test API-nøkkelen manuelt:
curl https://openrouter.ai/api/v1/models \
  -H "Authorization: Bearer $OPENROUTER_API_KEY"

# Sjekk at du har credit på OpenRouter:
# https://openrouter.ai/credits
```

### Problem: "Invalid HTTP request received"
Dette skjer hvis du ikke URL-encoder spesialtegn. Bruk:
```bash
# Korrekt (URL-encoded):
curl "http://localhost:4000/tilgjengelige-konsulenter/sammendrag?min_tilgjengelighet_prosent=50&p%C3%A5krevd_ferdighet=python"

# Eller bruk vanlig påkrevd_ferdighet (mange terminaler håndterer dette):
curl "http://localhost:4000/tilgjengelige-konsulenter/sammendrag?min_tilgjengelighet_prosent=50&påkrevd_ferdighet=python"
```

## Teknisk Stack

- **Python 3.11** - Programmeringsspråk
- **MCP (Model Context Protocol)** - Anthropic's standard for AI-integrasjoner
- **FastMCP** - Python framework for å bygge MCP servers
- **FastAPI** - REST API framework
- **Uvicorn** - ASGI server
- **OpenAI SDK** - For LLM-integrasjon via OpenRouter
- **Docker & Docker Compose** - Containerisering
- **OpenRouter** - LLM API gateway
- **GPT-4o-mini** - Language model for sammendrag

## Fordeler med MCP-arkitektur

1. **Standardisert protokoll**: Andre AI-assistenter kan enkelt koble til via MCP
2. **Type-safety**: Automatisk schema-generering fra Python type hints
3. **Discovery**: Klienter kan liste tilgjengelige verktøy dynamisk
4. **Security**: Process isolation mellom klient og server (stdio subprocess)
5. **Simplicitet**: Enkel kommunikasjon via JSON-RPC over stdin/stdout
6. **Fremtidssikker**: Native support i Claude Desktop og andre AI-verktøy

## Videre Utvikling

Mulige forbedringer:
- **Database**: Koble MCP server til PostgreSQL eller MongoDB
- **Flere tools**: Legg til verktøy for booking, rapportering, statistikk
- **Autentisering**: Legg til API-nøkkel autentisering på REST API
- **Caching**: Redis cache for å redusere LLM-calls
- **Streaming**: SSE (Server-Sent Events) for real-time updates
- **Claude Desktop**: Konfigurer for bruk direkte i Claude Desktop app
- **Metrics**: Prometheus/Grafana monitoring og metrics
- **Testing**: Unit tests og integration tests
- **CI/CD**: GitHub Actions pipeline for automatisk deploy
- **Kubernetes**: Deployment manifests for produksjon

## Referanser

- [MCP Dokumentasjon](https://modelcontextprotocol.io)
- [MCP Specification](https://spec.modelcontextprotocol.io)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Anthropic MCP Announcement](https://www.anthropic.com/news/model-context-protocol)
- [OpenRouter Documentation](https://openrouter.ai/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
