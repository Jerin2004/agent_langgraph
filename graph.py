"""LangGraph Workflow for Restaurant Order AI Agent."""

from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from state import OrderState
from nodes import (
    order_intake_node,
    order_confirmed_node,
    order_decision_node,
    handle_user_decision_node,
    cook_node,
    cook_decision_node,
    serve_node,
    serve_decision_node,
    apology_node,
    complete_node,
)


def route_from_start(state: OrderState) -> Literal["order_intake", "handle_user_decision"]:
    """Routes start of graph based on current state status."""
    status = state.get("status", "pending")
    # If waiting for user after partial or unavailable, route to decision handler
    if status in ["partial", "unavailable"]:
        return "handle_user_decision"
    return "order_intake"


def route_after_intake(state: OrderState) -> Literal["order_confirmed", "__end__"]:
    """Routes after order intake node."""
    status = state.get("status")
    if status == "rejected_unrelated":
        return END
    return "order_confirmed"


def route_after_decision(state: OrderState) -> Literal["cook", "__end__"]:
    """Routes after LLM order decision node."""
    status = state.get("status")
    if status == "confirmed":
        return "cook"
    # For "partial" and "unavailable", pause graph turn to wait for user input
    return END


def route_after_user_decision(state: OrderState) -> Literal["order_confirmed", "cook", "__end__"]:
    """Routes after processing user's decision."""
    status = state.get("status")
    if status == "confirmed":
        return "cook"
    elif status == "order_extracted":
        return "order_confirmed"
    return END


def route_after_cook_decision(state: OrderState) -> Literal["serve", "cook", "apology"]:
    """Routes after cook decision node."""
    status = state.get("status")
    cook_retries = state.get("cook_retry_count", 0)

    if status == "ready":
        return "serve"
    elif status == "cook_failed":
        if cook_retries > 0:
            return "cook"
        else:
            return "apology"
    return "apology"


def route_after_serve_decision(state: OrderState) -> Literal["order_complete", "cook", "apology"]:
    """Routes after serve decision node."""
    status = state.get("status")
    serve_retries = state.get("serve_retry_count", 0)
    cook_retries = state.get("cook_retry_count", 0)

    if status == "completed":
        return "order_complete"
    elif status == "serve_failed":
        if serve_retries <= 0 or cook_retries <= 0:
            return "apology"
        else:
            # Cook retry attempt is available, route back to cook
            return "cook"
    return "apology"


def create_order_graph(checkpointer=None):
    """Builds and compiles the restaurant order management LangGraph."""
    builder = StateGraph(OrderState)

    # 1. Add all nodes
    builder.add_node("order_intake", order_intake_node)
    builder.add_node("order_confirmed", order_confirmed_node)
    builder.add_node("order_decision", order_decision_node)
    builder.add_node("handle_user_decision", handle_user_decision_node)
    builder.add_node("cook", cook_node)
    builder.add_node("cook_decision", cook_decision_node)
    builder.add_node("serve", serve_node)
    builder.add_node("serve_decision", serve_decision_node)
    builder.add_node("apology", apology_node)
    builder.add_node("order_complete", complete_node)

    # 2. Add edges and conditional routing
    builder.add_conditional_edges(
        START,
        route_from_start,
        {
            "order_intake": "order_intake",
            "handle_user_decision": "handle_user_decision",
        }
    )

    builder.add_conditional_edges(
        "order_intake",
        route_after_intake,
        {
            "order_confirmed": "order_confirmed",
            END: END,
        }
    )

    builder.add_edge("order_confirmed", "order_decision")

    builder.add_conditional_edges(
        "order_decision",
        route_after_decision,
        {
            "cook": "cook",
            END: END,
        }
    )

    builder.add_conditional_edges(
        "handle_user_decision",
        route_after_user_decision,
        {
            "cook": "cook",
            "order_confirmed": "order_confirmed",
            END: END,
        }
    )

    builder.add_edge("cook", "cook_decision")

    builder.add_conditional_edges(
        "cook_decision",
        route_after_cook_decision,
        {
            "serve": "serve",
            "cook": "cook",
            "apology": "apology",
        }
    )

    builder.add_edge("serve", "serve_decision")

    builder.add_conditional_edges(
        "serve_decision",
        route_after_serve_decision,
        {
            "order_complete": "order_complete",
            "cook": "cook",
            "apology": "apology",
        }
    )

    builder.add_edge("apology", END)
    builder.add_edge("order_complete", END)

    if checkpointer is None:
        checkpointer = MemorySaver()

    return builder.compile(checkpointer=checkpointer)
