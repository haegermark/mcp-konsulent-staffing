# MCP Konsulent-Staffing

En **Model Context Protocol (MCP)** løsning for å finne tilgjengelige konsulenter basert på ferdigheter og kapasitet, med LLM-genererte sammendrag på norsk.

## Arkitektur

### MCP Server (konsulent-api)
- **Funksjon**: Eksponerer konsulent-data via MCP tool
- **Port**: Subprocess via stdio (ingen HTTP port)
- **Tool**: `hent_konsulenter()` - returnerer alle konsulenter som JSON

### MCP Client + REST API (llm-verktøy-api)
- **Funksjon**: Kobler til MCP server, filtrerer data, genererer LLM-sammendrag
- **Port**: 4000
- **LLM**: GPT-4o-mini via OpenRouter
- **Endpoints**:
  - `GET /tilgjengelige-konsulenter/sammendrag` - Hovedendepunkt
  - `GET /health` - Health check
  - `GET /docs` - API dokumentasjon (Swagger)

## Ports og URL-er

| Tjeneste | Port | URL |
|----------|------|-----|
| llm-verktøy-api | 4000 | http://localhost:4000 |
| konsulent-api (MCP) | - | Subprocess via stdio |

**Nøkkel URL-er**:
- API: `http://localhost:4000/tilgjengelige-konsulenter/sammendrag`
- Docs: `http://localhost:4000/docs`
- Health: `http://localhost:4000/health`

## Installasjon

### 1. Klon repository
```bash
git clone https://github.com/haegermark/mcp-konsulent-staffing.git
cd mcp-konsulent-staffing
```

### 2. Opprett .env-fil
```bash
echo "OPENROUTER_API_KEY=din-api-nøkkel-her" > .env
```

### 3. Start med Docker
```bash
docker compose up --build -d
```

### 4. Verifiser
```bash
curl http://localhost:4000/health
```

## Bruk

### Query Parametere

- **min_tilgjengelighet_prosent** (påkrevd): Integer 0-100
  - Tilgjengelighet = 100 - belastning_prosent
- **påkrevd_ferdighet** (valgfri): String
  - Enkelt: `"python"`
  - Flere: `"python,docker"` (AND-logikk)

### Eksempler

**Finn konsulenter med minst 50% tilgjengelighet og Python:**
```bash
curl "http://localhost:4000/tilgjengelige-konsulenter/sammendrag?min_tilgjengelighet_prosent=50&påkrevd_ferdighet=python"
```

**Flere ferdigheter (AND-logikk):**
```bash
curl "http://localhost:4000/tilgjengelige-konsulenter/sammendrag?min_tilgjengelighet_prosent=40&påkrevd_ferdighet=python,docker"
```

**Kun tilgjengelighet:**
```bash
curl "http://localhost:4000/tilgjengelige-konsulenter/sammendrag?min_tilgjengelighet_prosent=30"
```

**Response eksempel:**
```json
{
  "sammendrag": "Det ble funnet 2 konsulenter som oppfyller kriteriene om minimum 50% tilgjengelighet og ferdigheten python. Konsulentene er Fredrik med 50% tilgjengelighet, og Elias med 60% tilgjengelighet."
}
```

## Konsulentdata

| ID | Navn | Ferdigheter | Belastning | Tilgjengelighet |
|----|------|-------------|------------|-----------------|
| 1 | Fredrik | python, fastapi, docker | 50% | 50% |
| 2 | Elias | AI, data-science, matlab, mysql, java, python | 40% | 60% |
| 3 | Daniel | AI, ML, fastapi, django, pandas, postgresql, python, java, sql, javascript | 80% | 20% |
| 4 | Erlend | AI, data-science, c++, python | 60% | 40% |
| 5 | Adrian | AI, data-science, python, golang, kubernetes, docker | 70% | 30% |

## Docker Commands

```bash
# Start
docker compose up -d

# Rebuild
docker compose up --build -d

# Stopp
docker compose down

# Logs
docker logs llm-verktoy-api --follow

# Status
docker ps
```

## Prosjektstruktur

```
mcp-konsulent-staffing/
├── konsulent-api/           # MCP Server
│   ├── server.py           # FastMCP server
│   └── requirements.txt
├── llm-verktoy-api/        # MCP Client + REST API
│   ├── client.py           # FastAPI + LLM
│   └── requirements.txt
├── docker-compose.yml
├── .env
└── README.md
```

## MCP Flow

```
User → HTTP GET (localhost:4000)
  ↓
FastAPI (client.py)
  ↓
MCP Client (stdio)
  ↓
MCP Server (subprocess: server.py)
  ↓
Data Filtering
  ↓
LLM (GPT-4o-mini via OpenRouter)
  ↓
JSON Response
```

## Feilsøking

**Port 4000 i bruk:**
```bash
netstat -ano | findstr :4000
docker compose down
```

**Container starter ikke:**
```bash
docker logs llm-verktoy-api
cat .env  # Sjekk OPENROUTER_API_KEY
```

**MCP connection timeout:**
```bash
docker exec llm-verktoy-api ls -la /mcp-server/
docker logs llm-verktoy-api --tail 100
```

**LLM returnerer ikke sammendrag:**
```bash
docker exec llm-verktoy-api printenv | grep OPENROUTER
# Sjekk credit: https://openrouter.ai/credits
```

## Teknisk Stack

- **Python 3.11**
- **MCP** - Model Context Protocol (Anthropic)
- **FastMCP** - MCP server framework
- **FastAPI** - REST API
- **OpenAI SDK** - LLM integrasjon
- **GPT-4o-mini** - Language model
- **Docker** - Containerisering

## Hvorfor MCP?

| Aspekt | REST API | MCP |
|--------|----------|-----|
| Kommunikasjon | HTTP | JSON-RPC over stdio |
| Schema | Manuell | Auto-generert |
| Discovery | Manuell | Innebygd |
| Sikkerhet | Token-basert | Process isolation |
| AI-integrasjon | Custom | Native support |

## LLM Valg: GPT-4o-mini

**Hvorfor GPT-4o-mini?**
- Utmerket norsk språkstøtte
- Kostnadseffektiv ($0.15/$0.60 per M tokens)
- Rask responstid (<2s)
- OpenAI SDK integrasjon

**Alternativer:**
- GPT-4 Turbo: Dyrere, bedre kvalitet
- Claude 3.5 Sonnet: Dyrere, utmerket kvalitet
- Claude 3 Haiku: Billigere, svakere tekstgenerering

## Referanser

- [MCP Dokumentasjon](https://modelcontextprotocol.io)
- [MCP Specification](https://spec.modelcontextprotocol.io)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [FastMCP](https://github.com/jlowin/fastmcp)
- [OpenRouter](https://openrouter.ai/docs)
- [FastAPI](https://fastapi.tiangolo.com)
