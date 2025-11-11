"""
MCP Server for Konsulent API
Eksponerer verktøy for å hente og filtrere konsulenter
"""
from mcp.server.fastmcp import FastMCP
from typing import List, Optional
import json

# Initialiserer MCP server
mcp = FastMCP(name="Konsulent API Server")

# Hardkodet liste med konsulenter
KONSULENTER = [
    {
        "id": 1,
        "navn": "Fredrik",
        "ferdigheter": ["python", "fastapi", "docker"],
        "belastning_prosent": 50  # 50% tilgjengelig
    },
    {
        "id": 2,
        "navn": "Elias",
        "ferdigheter": ["artificial intelligence", "data-science", "software engineering",
                       "matlab", "mysql", "java", "python"],
        "belastning_prosent": 40  # 60% tilgjengelig
    },
    {
        "id": 3,
        "navn": "Daniel",
        "ferdigheter": ["artificial intelligence", "data-science", "software engineering",
                       "machine learning", "fastapi", "django", "pandas", "next.js",
                       "postgresql", "python", "java", "sql", "javascript"],
        "belastning_prosent": 80  # 20% tilgjengelig
    },
    {
        "id": 4,
        "navn": "Erlend",
        "ferdigheter": ["artificial intelligence", "data-science", "software engineering",
                       "c++", "python"],
        "belastning_prosent": 60  # 40% tilgjengelig
    },
    {
        "id": 5,
        "navn": "Adrian",
        "ferdigheter": ["artificial intelligence", "data-science", "software engineering",
                       "python", "golang", "kubernetes", "docker"],
        "belastning_prosent": 70  # 30% tilgjengelig
    },
]

@mcp.tool()
def hent_konsulenter() -> str:
    """
    Henter alle konsulenter med deres detaljer.

    Returnerer JSON-formatert liste med konsulenter inkludert:
    - id: Unik identifikator
    - navn: Konsulentens navn
    - ferdigheter: Liste med ferdigheter
    - belastning_prosent: Nåværende belastning i prosent (0-100)
    """
    return json.dumps(KONSULENTER, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    mcp.run()
