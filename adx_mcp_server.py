import os
from mcp.server.fastmcp import FastMCP
from azure.kusto.data import KustoClient, KustoConnectionStringBuilder
from azure.kusto.data.exceptions import KustoServiceError
from dotenv import load_dotenv

load_dotenv()

CLUSTER = os.getenv("ADX_CLUSTER_URI")
DATABASE = os.getenv("ADX_DATABASE")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
TENANT_ID = os.getenv("AZURE_TENANT_ID")


kcsb = KustoConnectionStringBuilder.with_aad_application_key_authentication(
    CLUSTER, CLIENT_ID, CLIENT_SECRET, TENANT_ID
)

client = KustoClient(kcsb)

# Create MCP server
mcp = FastMCP("ADX Query Executor")

@mcp.tool()
def run_adx_query(query: str) -> str:
    """Execute a Kusto (ADX) query and return the results as a string"""
    try:
        response = client.execute(DATABASE, query)
        rows = [str(row.to_dict()) for row in response.primary_results[0]]
        return "\n".join(rows)
    except KustoServiceError as e:
        return f"Query failed: {e}"

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
