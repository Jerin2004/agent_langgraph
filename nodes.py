"""Node functions for Restaurant Order AI Agent in LangGraph."""

import random
from typing import Any, Dict
from langchain_core.messages import AIMessage, HumanMessage

from state import OrderState
from menu import check_dish_availability, DEFAULT_MENU
from llm import extract_order_details


def order_intake_node(state: OrderState) -> Dict[str, Any]:
    """
    Node 1: Receives the user order, checks if related to food ordering,
    and extracts dish name and required quantity.
    """
    messages = state.get("messages", [])
    if not messages:
        return {
            "status": "pending",
            "messages": [AIMessage(content="Welcome to our restaurant! What dish and quantity would you like to order?")]
        }

    last_user_msg = messages[-1].content if messages else ""
    extraction = extract_order_details(last_user_msg, current_dish=state.get("dish_name"))

    # Case: Unrelated input
    if not extraction.is_food_related:
        reply = (
            "I am an AI food ordering assistant, not a general-purpose LLM. "
            "Please place a food order with a dish name and quantity (e.g., '2 pizzas' or '1 burger')."
        )
        return {
            "status": "rejected_unrelated",
            "final_result": "failed",
            "messages": [AIMessage(content=reply)]
        }

    # Food related order extracted
    dish = extraction.dish_name or "unknown"
    quantity = extraction.quantity if extraction.quantity is not None else 1

    order_retries = state.get("order_retry_count")
    if order_retries is None:
        order_retries = 3

    cook_retries = state.get("cook_retry_count")
    if cook_retries is None:
        cook_retries = 2

    serve_retries = state.get("serve_retry_count")
    if serve_retries is None:
        serve_retries = 2

    return {
        "dish_name": dish,
        "required_quantity": quantity,
        "order_retry_count": order_retries,
        "cook_retry_count": cook_retries,
        "serve_retry_count": serve_retries,
        "status": "order_extracted",
        "messages": [
            AIMessage(content=f"Received order: {quantity} {dish}. Checking menu availability...")
        ]
    }


def order_confirmed_node(state: OrderState) -> Dict[str, Any]:
    """
    Node 2: Looks at the menu and determines:
    - confirmed (fully available)
    - partial (partially available)
    - unavailable (dish not in menu or quantity is 0)
    Writes available_quantity and status into state.
    """
    dish_name = state.get("dish_name") or ""
    required_quantity = state.get("required_quantity") or 1

    status, available_quantity = check_dish_availability(dish_name, required_quantity)

    return {
        "available_quantity": available_quantity,
        "status": status
    }


def order_decision_node(state: OrderState) -> Dict[str, Any]:
    """
    LLM evaluates order status and informs the user.
    - If confirmed: proceeds to cook.
    - If partial: asks user if they want to proceed with partial or order something else.
    - If unavailable: asks user to reorder or informs them if retries are exhausted.
    """
    status = state.get("status")
    dish = state.get("dish_name", "dish")
    required = state.get("required_quantity", 1)
    available = state.get("available_quantity", 0)
    retries = state.get("order_retry_count", 3)

    if status == "confirmed":
        msg = f"Your order of {required} {dish} is confirmed and in stock! Sending to the kitchen to cook."
        return {
            "messages": [AIMessage(content=msg)]
        }

    elif status == "partial":
        msg = (
            f"We only have {available} {dish} available, but you requested {required}. "
            f"You have {retries} order retries remaining. "
            f"Would you like to proceed with the partial order of {available}, or place an order for something else?"
        )
        return {
            "messages": [AIMessage(content=msg)]
        }

    elif status == "unavailable":
        if retries <= 0:
            msg = (
                f"We apologize, {dish} is unavailable and you have exhausted all order retry attempts. "
                "Your order cannot be completed."
            )
            return {
                "status": "cancelled",
                "final_result": "failed",
                "messages": [AIMessage(content=msg)]
            }
        else:
            msg = (
                f"Sorry, {dish} is currently not available. "
                f"You have {retries} order retries remaining. Would you like to order something else?"
            )
            return {
                "messages": [AIMessage(content=msg)]
            }

    return {}


def handle_user_decision_node(state: OrderState) -> Dict[str, Any]:
    """
    Handles user decision after a partial or unavailable status.
    The user can either:
    1. Accept partial order
    2. Place a new order (decrements order_retry_count)
    3. Cancel / unsatisfied
    """
    messages = state.get("messages", [])
    last_text = messages[-1].content if messages else ""
    current_dish = state.get("dish_name")
    current_status = state.get("status")
    retries = state.get("order_retry_count", 3)

    extraction = extract_order_details(last_text, current_dish=current_dish)

    # 1. User accepts partial order
    if extraction.user_decision == "accept_partial" and current_status == "partial":
        available_qty = state.get("available_quantity", 1)
        msg = f"Confirmed! Proceeding with partial order of {available_qty} {current_dish}. Sending to kitchen to cook."
        return {
            "required_quantity": available_qty,
            "status": "confirmed",
            "messages": [AIMessage(content=msg)]
        }

    # 2. User cancels or rejects
    if extraction.user_decision == "cancel":
        msg = "Understood. Your order has been cancelled. Thank you for visiting!"
        return {
            "status": "cancelled",
            "final_result": "failed",
            "messages": [AIMessage(content=msg)]
        }

    # 3. User places a new order
    if extraction.is_food_related and extraction.dish_name:
        new_retries = retries - 1
        if new_retries <= 0:
            msg = (
                f"Order retry limit reached (0 attempts remaining). "
                f"We are unable to fulfill your order. Sincere apologies!"
            )
            return {
                "order_retry_count": 0,
                "status": "cancelled",
                "final_result": "failed",
                "messages": [AIMessage(content=msg)]
            }
        else:
            new_dish = extraction.dish_name
            new_qty = extraction.quantity or 1
            msg = f"Retrying order with: {new_qty} {new_dish}. ({new_retries} order retries left)."
            return {
                "dish_name": new_dish,
                "required_quantity": new_qty,
                "order_retry_count": new_retries,
                "status": "order_extracted",
                "messages": [AIMessage(content=msg)]
            }

    # Unrecognized response
    new_retries = retries - 1
    if new_retries <= 0:
        return {
            "order_retry_count": 0,
            "status": "cancelled",
            "final_result": "failed",
            "messages": [AIMessage(content="Order retry attempts exhausted. Order cancelled.")]
        }
    return {
        "order_retry_count": new_retries,
        "messages": [AIMessage(content=f"Could not understand your selection. Please specify a dish and quantity, or type 'cancel'. ({new_retries} order retries left)")]
    }


def cook_node(state: OrderState) -> Dict[str, Any]:
    """
    Node 3: Cook Node
    - Probability function: 60% chance of success, 40% chance of failure.
    - If cook fails, decrements cook_retry_count.
    """
    dish = state.get("dish_name", "dish")
    quantity = state.get("required_quantity", 1)
    cook_retries = state.get("cook_retry_count", 2)

    # Check for probability override (useful for testing)
    prob_override = state.get("cook_probability_override")
    if prob_override is not None:
        fail_prob = prob_override
    else:
        # Prompt requirement: 40% chance of fail, 60% chance of success
        fail_prob = 0.40

    # Simulate cooking
    roll = random.random()
    is_success = roll >= fail_prob

    if is_success:
        msg = f"Kitchen update: Cooking completed successfully! {quantity} {dish} is ready."
        return {
            "status": "ready",
            "messages": [AIMessage(content=msg)]
        }
    else:
        new_cook_retries = cook_retries - 1
        msg = f"Kitchen update: Cooking failed! Cook retries remaining: {new_cook_retries}."
        return {
            "status": "cook_failed",
            "cook_retry_count": new_cook_retries,
            "messages": [AIMessage(content=msg)]
        }


def cook_decision_node(state: OrderState) -> Dict[str, Any]:
    """
    Evaluates cook status.
    If cook failed and retry count is 0, issues LLM apology.
    """
    status = state.get("status")
    cook_retries = state.get("cook_retry_count", 0)
    dish = state.get("dish_name", "dish")

    if status == "cook_failed" and cook_retries <= 0:
        apology = (
            f"We sincerely apologize! Our kitchen failed to prepare your {dish} "
            "after multiple attempts. Your order could not be completed."
        )
        return {
            "final_result": "failed",
            "messages": [AIMessage(content=apology)]
        }

    return {}


def serve_node(state: OrderState) -> Dict[str, Any]:
    """
    Node 4: Serve Node
    - 2 cases: serve pass or serve fail.
    - 2 retry attempts.
    - If serve succeeds -> status = "completed"
    - If serve fails -> status = "serve_failed", decrements serve_retry_count.
    """
    dish = state.get("dish_name", "dish")
    quantity = state.get("required_quantity", 1)
    serve_retries = state.get("serve_retry_count", 2)

    prob_override = state.get("serve_probability_override")
    if prob_override is not None:
        fail_prob = prob_override
    else:
        # Default 30% chance of failure for serve simulation
        fail_prob = 0.30

    roll = random.random()
    is_success = roll >= fail_prob

    if is_success:
        msg = f"Serving update: Order successfully served to your table!"
        return {
            "status": "completed",
            "final_result": "completed",
            "messages": [AIMessage(content=msg)]
        }
    else:
        new_serve_retries = serve_retries - 1
        msg = f"Serving update: Serving failed (e.g. dropped tray or delivery issue). Serve retries remaining: {new_serve_retries}."
        return {
            "status": "serve_failed",
            "serve_retry_count": new_serve_retries,
            "messages": [AIMessage(content=msg)]
        }


def serve_decision_node(state: OrderState) -> Dict[str, Any]:
    """
    Evaluates serve status.
    - If completed: LLM issues final completion message.
    - If serve failed 2 times: LLM issues apology and ends.
    - If serve failed and retries remain: calls cook one more time to recook.
      Note: if cook has exhausted retry attempts, do not cook again and issue apology.
    """
    status = state.get("status")
    dish = state.get("dish_name", "dish")
    quantity = state.get("required_quantity", 1)
    serve_retries = state.get("serve_retry_count", 0)
    cook_retries = state.get("cook_retry_count", 0)

    if status == "completed":
        msg = f"Your order is complete! Here is your {quantity} {dish}. Enjoy your meal!"
        return {
            "final_result": "completed",
            "messages": [AIMessage(content=msg)]
        }

    if status == "serve_failed":
        if serve_retries <= 0:
            msg = (
                f"We sincerely apologize! Serving your {dish} failed after multiple attempts. "
                "Your order could not be completed."
            )
            return {
                "final_result": "failed",
                "messages": [AIMessage(content=msg)]
            }

        # Check if kitchen has retries left to recook
        if cook_retries <= 0:
            msg = (
                f"Serving failed, and our kitchen has exhausted all cooking retry attempts. "
                f"We cannot recook your {dish}. Sincere apologies!"
            )
            return {
                "final_result": "failed",
                "messages": [AIMessage(content=msg)]
            }
        else:
            msg = (
                f"Serving failed. Sending back to kitchen to cook again. "
                f"({serve_retries} serve retries left, {cook_retries} cook retries left)."
            )
            return {
                "messages": [AIMessage(content=msg)]
            }

    return {}


def apology_node(state: OrderState) -> Dict[str, Any]:
    """Issues final cancellation / apology message and marks final_result as failed."""
    return {
        "final_result": "failed",
        "status": "failed"
    }


def complete_node(state: OrderState) -> Dict[str, Any]:
    """Finalizes completed order state."""
    return {
        "final_result": "completed",
        "status": "completed"
    }
