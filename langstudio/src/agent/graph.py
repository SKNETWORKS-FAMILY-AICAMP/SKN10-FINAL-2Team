"""LangGraph single-node graph template.

Returns a predefined response. Replace logic and configuration as needed.
"""

from __future__ import annotations

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor
from neo4j import GraphDatabase

# Initialize OpenAI client
def get_llm(model_name="gpt-4o"):
    """Get LLM instance with appropriate configuration."""
    return ChatOpenAI(
        model=model_name,
        temperature=0.1
    )

# Neo4j connection
def get_neo4j_driver():
    """Get Neo4j database connection."""
    uri = "neo4j+ssc://4d5cd572.databases.neo4j.io"
    username = "neo4j"
    password = "Zx86I42iwxvqd5G2SUKdrLgDHuY62vhl037CfwnpgwY"
    return GraphDatabase.driver(uri, auth=(username, password))

def book_hotel(hotel_name: str):
    """Book a hotel"""
    return f"Successfully booked a stay at {hotel_name}."

def book_flight(from_airport: str, to_airport: str):
    """Book a flight"""
    return f"Successfully booked a flight from {from_airport} to {to_airport}."

flight_assistant = create_react_agent(
    model="openai:gpt-4o",
    tools=[book_flight],
    prompt="You are a flight booking assistant",
    name="flight_assistant"
)

hotel_assistant = create_react_agent(
    model="openai:gpt-4o",
    tools=[book_hotel],
    prompt="You are a hotel booking assistant",
    name="hotel_assistant"
)

graph = create_supervisor(
    agents=[flight_assistant, hotel_assistant],
    model=get_llm(),
    prompt=(
        "You manage a hotel booking assistant and a"
        "flight booking assistant. Assign work to them."
    )
).compile()

for chunk in graph.stream(
    {
        "messages": [
            {
                "role": "user",
                "content": "book a flight from BOS to JFK and a stay at McKittrick Hotel"
            }
        ]
    }
):
    print(chunk)
    print("\n")
