# LLM-VERKTØY-API: KLIENT-SIDE TJENESTE MED LLM-INTEGRASJON
#
# Dette er klient-siden i vår mikrotjenestearkitektur.
# Ansvar:
# 1. Hente data fra konsulent-api via MCP (Model Context Protocol)
# 2. Filtrere data basert på søkekriterier
# 3. Bruke LLM (GPT-4o-mini via OpenRouter) til å generere menneskeleselige sammendrag

from fastapi import FastAPI, Query, HTTPException
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from typing import Optional
from openai import AsyncOpenAI  # OpenAI SDK (brukes også for OpenRouter)
import json   # For JSON-formatering
import os     # For å lese environment variables

app = FastAPI(title="LLM Verktøy API", version="1.0.0")

# API-nøkkelen leses fra environment variable OPENROUTER_API_KEY
# Dette settes i docker-compose.yml fra .env filen.
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY environment variable must be set")

# OpenAI SDK konfigurert for OpenRouter
# OpenRouter er en gateway som gir tilgang til mange LLM-er via ett API
openai_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",  # OpenRouter sitt endpoint
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "http://localhost:4000",  # Påkrevd av OpenRouter
    }
)

MODEL = "openai/gpt-4o-mini"

# MCP server parameters - definerer hvordan vi kobler til konsulent-api
# Via stdio (standard input/output) kjører vi MCP serveren som en subprocess
server_params = StdioServerParameters(
    command="python",
    args=["/mcp-server/server.py"],
    env=None
)


# ============================================================================
# MCP KOMMUNIKASJON
# ============================================================================

async def call_mcp_tool(tool_name: str, arguments: dict) -> str:
    """
    Kaller et MCP-verktøy på konsulent-api serveren.

    MCP (Model Context Protocol) er Anthropic's protokoll for å koble
    AI-systemer til eksterne datakilder via JSON-RPC over stdio.

    Args:
        tool_name: Navnet på MCP-verktøyet som skal kalles
        arguments: Dictionary med argumenter til verktøyet

    Returns:
        JSON-streng med resultatet fra MCP-verktøyet
    """
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments=arguments)
            return result.content[0].text if result.content else ""


# ============================================================================
# DATABEHANDLING
# ============================================================================

def filter_konsulenter(konsulenter: list, min_tilgjengelighet: int, ferdighet: Optional[str]) -> list:
    """
    Filtrerer konsulenter basert på tilgjengelighet og ferdigheter.

    Tilgjengelighet beregnes som: 100 - belastning_prosent
    Eksempel: En konsulent med 40% belastning har 60% tilgjengelighet

    Args:
        konsulenter: Liste med alle konsulenter fra MCP server
        min_tilgjengelighet: Minimum tilgjengelighet i prosent (0-100)
        ferdighet: Påkrevd ferdighet(er), separert med komma.
                   Konsulenten må ha ALLE spesifiserte ferdigheter.

    Returns:
        Liste med filtrerte konsulenter, inkludert beregnet tilgjengelighet_prosent
    """
    filtered = []

    for k in konsulenter:
        # Beregn tilgjengelighet: 100% - belastning% = tilgjengelig%
        tilgjengelighet = 100 - k["belastning_prosent"]

        konsulent_ferdigheter = [f.lower() for f in k["ferdigheter"]]

        # SJEKK 1: Har konsulenten de påkrevde ferdighetene?
        if ferdighet:
            påkrevde_ferdigheter = [f.strip().lower() for f in ferdighet.split(',')]

            # Konsulenten må ha ALLE påkrevde ferdigheter (AND, ikke OR)
            har_alle_ferdigheter = all(
                ferd in konsulent_ferdigheter
                for ferd in påkrevde_ferdigheter
            )

            if not har_alle_ferdigheter:
                continue

        # SJEKK 2: Har konsulenten tilstrekkelig tilgjengelighet?
        har_tilstrekkelig_tilgjengelighet = tilgjengelighet >= min_tilgjengelighet

        if not har_tilstrekkelig_tilgjengelighet:
            continue

        # Hvis begge kriteriene er oppfylt, legg konsulenten til i resultatlisten
        filtered.append({
            "navn": k["navn"],
            "tilgjengelighet": tilgjengelighet,
            "ferdigheter": k["ferdigheter"]  # Beholder original kapitalisering
        })

    return filtered


# ============================================================================
# LLM INTEGRASJON
# ============================================================================

async def generer_sammendrag_med_llm(
    filtrerte_konsulenter: list,
    min_tilgjengelighet_prosent: int,
    påkrevd_ferdighet: Optional[str]
) -> str:
    """
    Bruker LLM til å generere et menneskeleselig sammendrag på norsk.

    Denne funksjonen tar filtrerte data og sender det til GPT-4o-mini
    for å få et naturlig, norskspråklig sammendrag.

    Args:
        filtrerte_konsulenter: Liste med filtrerte konsulenter
        min_tilgjengelighet_prosent: Minimum tilgjengelighet brukt i filtreringen
        påkrevd_ferdighet: Påkrevd ferdighet(er) brukt i filtreringen

    Returns:
        Menneskeleselig sammendrag på norsk fra GPT-4o-mini

    Raises:
        Exception: Hvis LLM-kallet feiler (ingen fallback)
    """

    # STEG 1: FORBERED DATA FOR LLM
    # Vi konverterer Python-listen til en pen JSON-streng.
    konsulent_data = json.dumps(filtrerte_konsulenter, ensure_ascii=False, indent=2)

    # STEG 2: KONSTRUER PROMPTS
    # System prompt: Definerer LLM-ens rolle og oppførsel
    system_prompt = """Du er en hjelpsom AI-assistent som spesialiserer deg på å oppsummere informasjon om konsulenter.
Du skal alltid svare på norsk med et klart og konsist sammendrag."""

    # User prompt: Den spesifikke oppgaven med all nødvendig kontekst:
    # - Søkekriteriene (for kontekst)
    # - De filtrerte dataene (som JSON)
    # - Klare instruksjoner for output-format
    user_prompt = f"""Basert på følgende søkekriterier:
- Minimum tilgjengelighet: {min_tilgjengelighet_prosent}%
- Påkrevd ferdighet: {påkrevd_ferdighet if påkrevd_ferdighet else 'Ingen spesifikk ferdighet'}

Filtrerte konsulenter som oppfyller kriteriene:
{konsulent_data}

Generer et kort, naturlig sammendrag på norsk (2-3 setninger) som:
1. Starter med hvor mange konsulenter som ble funnet
2. Nevner søkekriteriene
3. Lister hver konsulent med navn og tilgjengelighet
4. Bruker naturlig norsk språk

Hvis ingen konsulenter ble funnet, skriv en kort melding om det.

Returner BARE sammendraget, ingen ekstra forklaring."""

    # STEG 3: KALL LLM VIA OPENROUTER
    response = await openai_client.chat.completions.create(
        model=MODEL,  # "openai/gpt-4o-mini"
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,  # Moderat kreativitet - gir naturlig variasjon
        max_tokens=300    # Maks ~200-250 ord (nok for 2-3 setninger)
    )

    # STEG 4: EKSTRAHER OG RETURNER SAMMENDRAG
    sammendrag = response.choices[0].message.content.strip()
    return sammendrag


# ============================================================================
# API ENDEPUNKT
# ============================================================================

# API ENDEPUNKT: GET /tilgjengelige-konsulenter/sammendrag
#
# Hovedendepunktet i denne tjenesten. Dette er stedet hvor all logikk skjer:
# 1. Hente data fra konsulent-api via MCP
# 2. Filtrere basert på tilgjengelighet og ferdigheter
# 3. Generere sammendrag med LLM
#
# URL: http://localhost:5000/tilgjengelige-konsulenter/sammendrag
#
# Query parametere:
# - min_tilgjengelighet_prosent: Minimum % tilgjengelig (0-100), påkrevd
# - påkrevd_ferdighet: Ferdighet(er) som kreves, kommaseparert, valgfri

@app.get("/tilgjengelige-konsulenter/sammendrag")
async def get_tilgjengelige_konsulenter_sammendrag(
    min_tilgjengelighet_prosent: int = Query(
        ...,  # ... betyr at parameteren er påkrevd
        ge=0,
        le=100,
        description="Minimum tilgjengelighet i prosent (0-100)"
    ),
    påkrevd_ferdighet: Optional[str] = Query(
        None,
        description="Ferdighet(er) som må være til stede hos konsulenten. Bruk komma for flere: 'python,fastapi'"
    )
):
    """
    Henter konsulenter fra konsulent-api via MCP, filtrerer basert på tilgjengelighet og ferdigheter,
    og returnerer et menneskeleselig sammendrag generert av LLM.

    Tilgjengelighet beregnes som: 100 - belastning_prosent

    Flere ferdigheter kan spesifiseres med komma-separering (f.eks. "python,fastapi").
    Konsulenten må ha ALLE de spesifiserte ferdighetene (AND-logikk, ikke OR).

    Returnerer et JSON-objekt med LLM-generert sammendrag på norsk.

    Eksempler:
        GET /tilgjengelige-konsulenter/sammendrag?min_tilgjengelighet_prosent=50&påkrevd_ferdighet=python
        GET /tilgjengelige-konsulenter/sammendrag?min_tilgjengelighet_prosent=40&påkrevd_ferdighet=python,docker
    """

    try:
        # STEG 1: HENT DATA FRA MCP SERVER
        konsulenter_data = await call_mcp_tool("hent_konsulenter", {})
        konsulenter = json.loads(konsulenter_data)

        # STEG 2: FILTRER KONSULENTER
        # Vi går gjennom alle konsulenter og filtrerer basert på:
        # 1. Tilgjengelighet >= min_tilgjengelighet_prosent
        # 2. Har ALLE påkrevde ferdigheter (AND-logikk)
        filtrerte_konsulenter = filter_konsulenter(
            konsulenter,
            min_tilgjengelighet_prosent,
            påkrevd_ferdighet
        )

        # STEG 3: GENERER SAMMENDRAG MED LLM
        # Vi sender de filtrerte konsulentene til vår LLM-funksjon.
        sammendrag = await generer_sammendrag_med_llm(
            filtrerte_konsulenter=filtrerte_konsulenter,
            min_tilgjengelighet_prosent=min_tilgjengelighet_prosent,
            påkrevd_ferdighet=påkrevd_ferdighet
        )

        # STEG 4: RETURNER RESULTAT
        # Vi returnerer et JSON-objekt med sammendraget.
        return {"sammendrag": sammendrag}

    except Exception as e:
        # Hvis noe går galt (MCP-feil, LLM-feil, etc.)
        # returnerer vi en 500 Internal Server Error til klienten
        raise HTTPException(
            status_code=500,
            detail=f"Feil: {str(e)}"
        )


# API ENDEPUNKT: GET /health
@app.get("/health")
async def health_check():
    """
    Health check endepunkt for å verifisere at tjenesten kjører.

    Brukes av Docker healthcheck og monitoring-verktøy.
    """
    return {"status": "ok", "type": "MCP Client"}


# Kjør applikasjonen hvis filen kjøres direkte
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4000)
