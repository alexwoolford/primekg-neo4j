from langchain_anthropic import ChatAnthropic
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from .config import settings
from .prompts import SYSTEM_PROMPT


def get_mcp_client():
    command = settings.neo4j_mcp_command
    if command == "uvx":
        args = ["mcp-neo4j-cypher@latest", "--transport", "stdio"]
    else:
        args = []
    env = {
        "NEO4J_URI": settings.neo4j_uri,
        "NEO4J_USERNAME": settings.neo4j_user,
        "NEO4J_PASSWORD": settings.neo4j_password,
        "NEO4J_DATABASE": settings.neo4j_database,
        "NEO4J_READ_ONLY": "true",
        "NEO4J_LOG_LEVEL": "error",
        "NEO4J_TELEMETRY": "false",
    }
    return MultiServerMCPClient(
        {
            "neo4j": {
                "command": command,
                "args": args,
                "transport": "stdio",
                "env": env,
            }
        }
    )


async def build_agent(mcp_client):
    tools = await mcp_client.get_tools()
    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        temperature=0,
        max_tokens=4096,
    )
    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=SYSTEM_PROMPT,
        checkpointer=MemorySaver(),
    )
    return agent
