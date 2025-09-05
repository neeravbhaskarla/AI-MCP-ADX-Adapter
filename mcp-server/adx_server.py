import os
import logging
import sys
from dotenv import load_dotenv

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from azure.kusto.data import KustoClient, KustoConnectionStringBuilder
from azure.kusto.data.exceptions import KustoServiceError

# Load environment variables from .env file
load_dotenv()

# Suppress all logging output
logging.basicConfig(level=logging.CRITICAL)

# --- env/config ---
CLUSTER = os.getenv("ADX_CLUSTER_URI")
DATABASE = os.getenv("ADX_DATABASE")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
TENANT = os.getenv("AZURE_TENANT_ID")

if not CLUSTER or not DATABASE:
    print("Error: ADX_CLUSTER_URI and ADX_DATABASE must be set in .env file", file=sys.stderr)
    sys.exit(1)
if not CLIENT_ID or not CLIENT_SECRET or not TENANT:
    print("Error: AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, and AZURE_TENANT_ID must be set in .env file", file=sys.stderr)
    sys.exit(1)

# --- ADX client factory ---
def make_client() -> KustoClient:
    kcsb = KustoConnectionStringBuilder.with_aad_application_key_authentication(
        CLUSTER, CLIENT_ID, CLIENT_SECRET, TENANT
    )
    return KustoClient(kcsb)

# Create FastMCP instance without banner
mcp = FastMCP("adx-mcp")

# -------- Tool Schemas --------
class QueryInput(BaseModel):
    kql: str = Field(description="KQL query to run against the ADX database")

# -------- Tools --------
@mcp.tool
def adx_query(input: QueryInput) -> str:
    """
    Run a KQL query and return a compact text table.
    """
    client = make_client()
    try:
        r = client.execute(DATABASE, input.kql)
        primary = r.primary_results[0]
        cols = [c.column_name for c in primary.columns]
        lines = [" | ".join(cols)]
        for row in primary.rows:
            lines.append(" | ".join(str(row[c]) for c in cols))
        return "\n".join(lines) if lines else "(no rows)"
    except KustoServiceError as e:
        return f"ADX error: {str(e)}"

if __name__ == "__main__":
    # Run as a TCP MCP server on localhost. Use env MCP_HOST/MCP_PORT to override.
    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "8765"))

    print(f"Starting MCP TCP server on {host}:{port} (FastMCP) ...")

    # Suppress FastMCP banner by redirecting stderr temporarily, but keep a handle
    original_stderr = sys.stderr
    suppressed_stderr = open(os.devnull, 'w')
    sys.stderr = suppressed_stderr
    try:
        try:
            # Disable uvicorn access log and lower overall server verbosity via uvicorn_config
            uvicorn_cfg = {"access_log": False, "log_level": "critical"}
            mcp.run(transport="streamable-http", host=host, port=port, uvicorn_config=uvicorn_cfg)
        except Exception as exc:
            sys.stderr = original_stderr
            suppressed_stderr.close()
            print(f"ERROR: MCP server failed to start: {exc}", file=original_stderr)
            raise
    finally:
        try:
            suppressed_stderr.close()
        except Exception:
            pass
        sys.stderr = original_stderr
