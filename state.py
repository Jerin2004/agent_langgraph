"""LangGraph State Definition for Restaurant Order AI Agent."""

from typing import Annotated, Optional, Sequence
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class OrderState(TypedDict):
    """
    LangGraph state matching the architecture in prompt.md:
    
    1. messages: Annotated message sequence between LLM and user
    2. order details:
       - dish_name: str
       - required_quantity: int
       - available_quantity: int (written by order_confirmed from menu)
    3. status: Updated by each node
    4. retry counters:
       - order_retry_count: 3 attempts
       - cook_retry_count: 2 attempts
       - serve_retry_count: 2 attempts
    5. final_result: "completed" or "failed"
    """
    # Conversation history
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # Order details
    dish_name: Optional[str]
    required_quantity: Optional[int]
    available_quantity: Optional[int]

    # Node status tracking
    # E.g.: "pending", "confirmed", "partial", "unavailable",
    #       "ready", "cook_failed", "completed", "serve_failed",
    #       "cancelled", "rejected_unrelated"
    status: str

    # Retry counters
    order_retry_count: int  # 3 attempts
    cook_retry_count: int   # 2 attempts
    serve_retry_count: int  # 2 attempts

    # Final result: whether order was completed or not
    final_result: Optional[str]  # "completed" or "failed"

    # Optional control flags for testing / simulation overrides
    cook_probability_override: Optional[float]
    serve_probability_override: Optional[float]
