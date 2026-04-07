import asyncio
import warnings

warnings.filterwarnings("ignore", message="Core Pydantic V1 functionality")

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from .agent import build_agent, get_mcp_client  # noqa: E402


async def run():
    print("PrimeKG Chatbot (type 'quit' to exit)")

    mcp_client = get_mcp_client()
    agent = await build_agent(mcp_client)
    config = {"configurable": {"thread_id": "session-primekg"}}

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input or user_input.lower() in ("quit", "exit", "q"):
            break

        try:
            result = await agent.ainvoke(
                {"messages": [("user", user_input)]},
                config=config,
            )
            ai_message = result["messages"][-1]
            print(f"\nAssistant: {ai_message.content}")
        except Exception as e:
            print(f"\nError: {e}")


def main():
    asyncio.run(run())
