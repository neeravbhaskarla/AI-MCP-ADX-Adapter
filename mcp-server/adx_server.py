import os
import logging
from typing import Optional

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from azure.kusto.data import KustoClient, KustoConnectionStringBuilder
from azure.kusto.data.exceptions import KustoServiceError

# Disable FastMCP banner
os.environ["FASTMCP_NO_BANNER"] = "1"

# --- logging to STDERR (never stdout for stdio servers) ---
logging.basicConfig(level=logging.WARNING)

# --- env/config ---
CLUSTER = os.environ["ADX_CLUSTER_URI"]
DATABASE = os.environ["ADX_DATABASE"]
TENANT = os.environ.get("AZURE_TENANT_ID") 

# --- ADX client factory ---
def make_client() -> KustoClient:
    kcsb = KustoConnectionStringBuilder.with_az_cli_authentication(CLUSTER)
    if TENANT:
        kcsb.authority_id = TENANT
    return KustoClient(kcsb)

import sys
import io
# Suppress FastMCP banner
original_stderr = sys.stderr
sys.stderr = io.StringIO()
mcp = FastMCP("adx-mcp")
sys.stderr = original_stderr

# -------- Tool Schemas --------
class QueryInput(BaseModel):
    kql: str = Field(description="KQL query to run against the ADX database")

class IngestInlineInput(BaseModel):
    table: str = Field(description="Target table")
    payload: str = Field(description="Inline data rows")
    data_format: str = Field("csv", description="Format: 'csv' or 'json'")

class CreateTableInput(BaseModel):
    table: str = Field(description="Table name")
    schema_kql: str = Field(
        description="Columns in Kusto syntax, e.g. 'Timestamp:datetime, Level:string, Message:string'"
    )

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
        # Build a tiny plain-text table for portability
        cols = [c.column_name for c in primary.columns]
        lines = [" | ".join(cols)]
        for row in primary.rows:
            lines.append(" | ".join(str(row[c]) for c in cols))
        return "\n".join(lines) if lines else "(no rows)"
    except KustoServiceError as e:
        return f"ADX error: {str(e)}"

@mcp.tool
def adx_ingest_inline(input: IngestInlineInput) -> str:
    """
    Ingest small test data directly using a control command.
    For CSV, provide rows without header, e.g.:
    '2025-09-04T10:00:00Z,INFO,Hello,AuthService,vm01,user1'
    """
    cmd = (
        f".ingest inline into table {input.table} <|\n{input.payload}"
        if input.data_format.lower() == "csv"
        else f".ingest inline into table {input.table} with (format='json') <|\n{input.payload}"
    )
    client = make_client()
    try:
        client.execute_mgmt(DATABASE, cmd)
        return "Ingest submitted."
    except KustoServiceError as e:
        return f"Ingest failed: {str(e)}"

@mcp.tool
def adx_create_table(input: CreateTableInput) -> str:
    """
    Create a table using Kusto column syntax.
    Example: schema_kql='Timestamp:datetime, Level:string, Message:string, Service:string, Host:string, UserId:string'
    """
    cmd = f".create table {input.table} ({input.schema_kql})"
    client = make_client()
    try:
        client.execute_mgmt(DATABASE, cmd)
        return f"Table '{input.table}' created."
    except KustoServiceError as e:
        return f"Create failed: {str(e)}"

if __name__ == "__main__":
    # stdio transport; avoid print() to stdout
    mcp.run(transport="stdio")
