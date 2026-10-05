"""Automated Simulation and Test Suite for Restaurant Order AI Agent."""

import uuid
from typing import List, Tuple
from langchain_core.messages import HumanMessage
from graph import create_order_graph
from menu import DEFAULT_MENU


def run_scenario(
    name: str,
    user_inputs: List[str],
    cook_override: float = 0.0,   # 0.0 means 0% fail (100% success)
    serve_override: float = 0.0,  # 0.0 means 0% fail (100% success)
) -> dict:
    """Executes a multi-turn scenario and returns final state."""
    app = create_order_graph()
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    print(f"\n{'='*70}")
    print(f"🧪 SCENARIO: {name}")
    print(f"{'='*70}")

    last_result = None
    for idx, user_input in enumerate(user_inputs, 1):
        print(f"\n[Turn {idx}] User: \"{user_input}\"")
        inputs = {
            "messages": [HumanMessage(content=user_input)],
            "cook_probability_override": cook_override,
            "serve_probability_override": serve_override,
        }
        last_result = app.invoke(inputs, config=config)

        # Print agent's response for this turn
        messages = last_result.get("messages", [])
        for msg in reversed(messages):
            if msg.type == "ai":
                print(f"Agent: {msg.content}")
                break

    print(f"\nFinal State Summary:")
    print(f"  • Dish: {last_result.get('dish_name')}")
    print(f"  • Req Quantity: {last_result.get('required_quantity')}")
    print(f"  • Available Quantity: {last_result.get('available_quantity')}")
    print(f"  • Status: {last_result.get('status')}")
    print(f"  • Order Retries Left: {last_result.get('order_retry_count')}")
    print(f"  • Cook Retries Left: {last_result.get('cook_retry_count')}")
    print(f"  • Serve Retries Left: {last_result.get('serve_retry_count')}")
    print(f"  • Final Result: {last_result.get('final_result')}")
    return last_result


def run_all_tests():
    print("\n" + "#"*70)
    print("  RUNNING ALL SIMULATION TEST CASES FOR RESTAURANT AI AGENT")
    print("#"*70)

    test_results: List[Tuple[str, bool, str]] = []

    # Test 1: Unrelated Input Rejection
    res1 = run_scenario(
        name="1. Unrelated User Input Rejection",
        user_inputs=["What is the capital of France?"],
    )
    p1 = (
        res1.get("status") == "rejected_unrelated"
        and res1.get("final_result") == "failed"
    )
    test_results.append(("1. Unrelated Input Rejection", p1, f"Status: {res1.get('status')}"))

    # Test 2: Standard Valid Order (Fully Available)
    res2 = run_scenario(
        name="2. Full Available Order (2 Burgers)",
        user_inputs=["I want 2 burgers"],
        cook_override=0.0,
        serve_override=0.0
    )
    p2 = (
        res2.get("status") == "completed"
        and res2.get("final_result") == "completed"
        and res2.get("required_quantity") == 2
    )
    test_results.append(("2. Full Available Order", p2, f"Status: {res2.get('status')}"))

    # Test 3: Unavailable Dish with Successful Retry
    res3 = run_scenario(
        name="3. Unavailable Item (Salad) -> Retry With Pizza",
        user_inputs=["I want 1 salad", "I would like 2 pizzas instead"],
        cook_override=0.0,
        serve_override=0.0
    )
    p3 = (
        res3.get("status") == "completed"
        and res3.get("final_result") == "completed"
        and res3.get("dish_name") == "pizza"
        and res3.get("order_retry_count") == 2
    )
    test_results.append(("3. Unavailable Item -> Reorder", p3, f"Status: {res3.get('status')}, Retries: {res3.get('order_retry_count')}"))

    # Test 4: Partial Availability -> User Accepts Partial
    # Menu has 2 pasta available, user requests 5
    res4 = run_scenario(
        name="4. Partial Availability (5 Pasta) -> User Accepts Partial (2)",
        user_inputs=["I want 5 pastas", "yes, proceed with 2"],
        cook_override=0.0,
        serve_override=0.0
    )
    p4 = (
        res4.get("status") == "completed"
        and res4.get("final_result") == "completed"
        and res4.get("required_quantity") == 2
    )
    test_results.append(("4. Partial Availability -> Accept Partial", p4, f"Quantity: {res4.get('required_quantity')}"))

    # Test 5: Partial Availability -> User Rejects and Cancels
    res5 = run_scenario(
        name="5. Partial Availability -> User Cancels",
        user_inputs=["I want 5 pastas", "cancel"],
        cook_override=0.0,
        serve_override=0.0
    )
    p5 = (
        res5.get("status") == "cancelled"
        and res5.get("final_result") == "failed"
    )
    test_results.append(("5. Partial Availability -> User Cancels", p5, f"Status: {res5.get('status')}"))

    # Test 6: Cook Failure with Exhausted Retries
    # cook_override=1.0 means 100% fail
    res6 = run_scenario(
        name="6. Cook Failure with Exhausted Retries",
        user_inputs=["I want 1 burger"],
        cook_override=1.0,  # Cook fails every time
    )
    p6 = (
        res6.get("cook_retry_count") <= 0
        and res6.get("final_result") == "failed"
    )
    test_results.append(("6. Cook Failure Exhaustion", p6, f"Cook retries: {res6.get('cook_retry_count')}, Result: {res6.get('final_result')}"))

    # Test 7: Serve Failure with Exhausted Retries
    # Cook succeeds, but serve fails every time (serve_override=1.0)
    res7 = run_scenario(
        name="7. Serve Failure with Exhausted Retries",
        user_inputs=["I want 1 pizza"],
        cook_override=0.0,
        serve_override=1.0  # Serve fails every time
    )
    p7 = (
        res7.get("serve_retry_count") <= 0
        and res7.get("final_result") == "failed"
    )
    test_results.append(("7. Serve Failure Exhaustion", p7, f"Serve retries: {res7.get('serve_retry_count')}, Result: {res7.get('final_result')}"))

    # Test 8: Serve Failure with Cook Recovery (cook retry > 0, recook succeeds, then serve succeeds)
    # To simulate: 1st cook passes, 1st serve fails, 2nd cook passes, 2nd serve passes
    # We can test by having cook_override=0.0 and a custom override or testing cook retry check
    # Let's test Exhausted Order Retries (3 order attempts for unavailable items)
    res8 = run_scenario(
        name="8. Exhausted Order Retry Attempts (3 Retries)",
        user_inputs=[
            "I want 1 salad",               # Unavailable (Attempt 1: retries 3 left)
            "I want 1 salad again",         # Unavailable (Attempt 2: retries 2 left)
            "give me salad one more time",  # Unavailable (Attempt 3: retries 1 left)
            "still want salad"              # Unavailable (Attempt 4: retries exhausted -> 0)
        ],
        cook_override=0.0,
        serve_override=0.0
    )
    p8 = (
        res8.get("order_retry_count") <= 0
        and res8.get("final_result") == "failed"
    )
    test_results.append(("8. Exhausted Order Retries", p8, f"Order retries: {res8.get('order_retry_count')}, Result: {res8.get('final_result')}"))

    # Summary report
    print("\n" + "=" * 70)
    print("                    TEST EXECUTION SUMMARY REPORT")
    print("=" * 70)
    total = len(test_results)
    passed = sum(1 for _, ok, _ in test_results if ok)
    for name, ok, details in test_results:
        mark = "✅ PASS" if ok else "❌ FAIL"
        print(f"  {mark:<9} | {name:<45} | {details}")
    print("-" * 70)
    print(f"Total: {total} | Passed: {passed} | Failed: {total - passed}")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()
