"""Interactive CLI for Restaurant Order AI Agent using LangGraph."""

import sys
import uuid
from langchain_core.messages import HumanMessage
from graph import create_order_graph
from menu import DEFAULT_MENU


def print_banner():
    print("=" * 65)
    print(" 🍽️   RESTAURANT ORDER MANAGEMENT AI AGENT (LangGraph)  🍽️ ")
    print("=" * 65)
    print("Current Available Menu:")
    for dish, qty in DEFAULT_MENU.items():
        status_str = f"{qty} in stock" if qty > 0 else "OUT OF STOCK"
        print(f"  • {dish.capitalize():<12} : {status_str}")
    print("-" * 65)
    print("Rules & Constraints:")
    print("  • Order limit: 1 dish + desired quantity")
    print("  • Order retry attempts: 3")
    print("  • Cook retry attempts: 2 (60% success, 40% fail probability)")
    print("  • Serve retry attempts: 2")
    print("=" * 65)
    print()


def run_interactive_agent():
    print_banner()
    app = create_order_graph()
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    # Initial state
    state = {
        "messages": [],
        "dish_name": None,
        "required_quantity": None,
        "available_quantity": None,
        "status": "pending",
        "order_retry_count": 3,
        "cook_retry_count": 2,
        "serve_retry_count": 2,
        "final_result": None,
        "cook_probability_override": None,
        "serve_probability_override": None,
    }

    print("Agent: Hello! Welcome to our restaurant. What would you like to order today?")

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting. Thank you!")
            sys.exit(0)

        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break

        # Pass user message into the graph
        inputs = {
            "messages": [HumanMessage(content=user_input)]
        }

        # Run graph turn
        result = app.invoke(inputs, config=config)

        # Print assistant messages from this turn
        messages = result.get("messages", [])
        if messages:
            # Print the most recent messages generated in this run
            print(f"\n[Status: {result.get('status')} | Dish: {result.get('dish_name')} | Qty: {result.get('required_quantity')}]")
            print(f"[Retries Left -> Order: {result.get('order_retry_count')}, Cook: {result.get('cook_retry_count')}, Serve: {result.get('serve_retry_count')}]")
            print("-" * 50)
            # Find any recent AIMessages
            for msg in reversed(messages):
                if msg.type == "ai":
                    print(f"Agent: {msg.content}")
                    break

        # Check if process has terminated (final_result is set)
        final_result = result.get("final_result")
        if final_result:
            print("\n" + "=" * 50)
            if final_result == "completed":
                print("🎉 ORDER COMPLETED SUCCESSFULLY! ENJOY YOUR MEAL! 🎉")
            else:
                print("❌ ORDER PROCESS TERMINATED: FAILED / CANCELLED ❌")
            print(f"Final Status: {result.get('status')}")
            print("=" * 50)
            break


if __name__ == "__main__":
    run_interactive_agent()
