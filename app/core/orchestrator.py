from app.utils.prompts import SYSTEM_PROMPT
from app.core.rag.tool_loader import retrievers
from llama_index.core import Settings
from pydantic_ai import Agent
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from pydantic import BaseModel
from typing import List, Optional, Any
from pydantic_ai.messages import ModelMessage

Settings.llm = OpenAI(
    model="gpt-4o",
)

Settings.embed_model = OpenAIEmbedding(
    model="text-embedding-3-small", embed_batch_size=100
)


class Output(BaseModel):
    answer: str
    sources: list
    confidence: float
    retriever_type: str


def generate_agent(message_history: Optional[List[ModelMessage]] = None) -> Agent:
    """
    Generate an agent for the OpenAI model with the specified system prompt and retrievers.
    
    Args:
        message_history: Optional list of previous chat messages to maintain context
        
    Returns:
        Initialized agent
    """
    # Initialize the agent with the system prompt and retrievers
    agent = Agent(
        'openai:gpt-4o',
        instructions=SYSTEM_PROMPT if message_history is None else None,  
        tools=retrievers,
        verbose=True,
        output_type=Output,
        message_history=message_history
    )
    
    return agent


def combine_message_histories(existing_history: List[ModelMessage], new_messages: List[ModelMessage]) -> List[ModelMessage]:
    """
    Combine existing message history with new messages, avoiding duplicates.
    
    Args:
        existing_history: The existing message history
        new_messages: New messages to add
        
    Returns:
        Combined message history
    """
    # Create a set of existing message IDs to avoid duplicates
    existing_ids = set()
    for msg in existing_history:
        if hasattr(msg, 'id'):
            existing_ids.add(msg.id)
    
    # Start with the existing history
    combined = list(existing_history)
    
    # Add new messages that aren't already in the history
    for msg in new_messages:
        if not hasattr(msg, 'id') or msg.id not in existing_ids:
            combined.append(msg)
    
    return combined


def truncate_message_history(message_history: List[ModelMessage], max_messages: int = 10) -> List[ModelMessage]:
    """
    Truncate message history to a maximum number of messages, keeping the most recent ones.
    
    Args:
        message_history: The message history to truncate
        max_messages: Maximum number of messages to keep
        
    Returns:
        Truncated message history
    """
    if len(message_history) <= max_messages:
        return message_history
    
    # Keep system messages and the most recent messages
    system_messages = [msg for msg in message_history if msg.kind == "system"]
    other_messages = [msg for msg in message_history if msg.kind != "system"]
    
    # Take the most recent messages
    recent_messages = other_messages[-max_messages:]
    
    # Combine system messages with recent messages
    return system_messages + recent_messages


if __name__ == "__main__":
    # Example usage
    agent = generate_agent()

    # Run the agent with a sample query using a synchronous method
    result = agent.run_sync(
        "What is the role of the Kenya Film Commission in the film industry?"
    )
    print(result.output)
    
    # Example of continuing a conversation with the same context
    follow_up_agent = generate_agent(message_history=result.all_messages())
    follow_up_result = follow_up_agent.run_sync(
        "Can you elaborate on their support for filmmakers?"
    )
    print(follow_up_result.output)

    # Run the agent with a sample query using an asynchronous method
    # result = await agent.run(
    #     "What is the role of the Kenya Film Commission in the film industry?",
    #     chat_history=[],
    # )

    # The output will be an instance of the Output model





