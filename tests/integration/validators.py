"""
Custom validators for Tavern integration tests.

This module provides custom validation functions for testing API responses
that require more complex validation than Tavern's built-in capabilities.
"""


def validate_exact_text(response, expected_text):
    import json

    # Get response body as text
    if hasattr(response, "text"):
        body_text = response.text
    elif hasattr(response, "content"):
        body_text = (
            response.content.decode("utf-8")
            if isinstance(response.content, bytes)
            else str(response.content)
        )
    else:
        body_text = str(response)

    # For SSE streaming responses, extract and combine all text content
    combined_text = ""
    lines = body_text.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Handle SSE format - strip "data: " prefix
        json_line = line
        if line.startswith("data: "):
            json_line = line[6:]  # Remove "data: " prefix

        # Skip [DONE] markers
        if json_line == "[DONE]":
            continue

        try:
            # Parse JSON line
            json_data = json.loads(json_line)

            # Handle simplified response format - accumulate text deltas
            if json_data.get("type") == "response" and "delta" in json_data:
                combined_text += json_data.get("delta", "")
            elif json_data.get("type") == "error":
                raise AssertionError(
                    f"Error from backend: {json_data.get('message', 'Unknown error')}"
                )

        except (json.JSONDecodeError, KeyError):
            # Skip lines that aren't valid JSON
            continue

    # Check if expected text is contained in the combined text
    if expected_text in combined_text:
        return True

    raise AssertionError(
        f"Expected text '{expected_text}' not found in response. "
        f"Combined text from streaming chunks: '{combined_text}' "
        f"Raw response body: {body_text[:500]}..."  # Show first 500 chars
    )


def validate_session_messages(
    response,
    expected_message_count: int = None,
    expected_user_messages: list = None,
    expected_first_message: str = None,
):
    """
    Validate session messages response structure and content.

    This validator checks that session messages are properly formatted and
    contain the expected content for session switching tests.

    Args:
        response: Tavern response object
        expected_message_count: Expected number of messages in response
        expected_user_messages: List of expected user message texts
        expected_first_message: Expected text of the first message

    Returns:
        bool: True if validation passes

    Raises:
        AssertionError: If validation fails
    """
    try:
        # Parse JSON response
        if hasattr(response, "json"):
            session_data = response.json()
        else:
            import json

            session_data = json.loads(response.text)

        # Check that messages field exists
        assert "messages" in session_data, "Response missing 'messages' field"
        messages = session_data["messages"]

        # Check message count if specified
        if expected_message_count is not None:
            assert (
                len(messages) == expected_message_count
            ), f"Expected {expected_message_count} messages, got {len(messages)}"

        # Check specific user messages if specified
        if expected_user_messages:
            user_messages = [msg for msg in messages if msg.get("role") == "user"]
            user_texts = []
            for msg in user_messages:
                for content_item in msg.get("content", []):
                    if content_item.get("type") == "input_text":
                        user_texts.append(content_item.get("text", ""))

            for expected_text in expected_user_messages:
                assert (
                    expected_text in user_texts
                ), f"Expected user message '{expected_text}' not found in {user_texts}"

        # Check first message if specified
        if expected_first_message and messages:
            first_message = messages[0]
            if first_message.get("role") == "user":
                first_text = ""
                for content_item in first_message.get("content", []):
                    if content_item.get("type") == "input_text":
                        first_text = content_item.get("text", "")
                        break
                assert (
                    first_text == expected_first_message
                ), f"Expected first message '{expected_first_message}', got '{first_text}'"

        # Validate message structure
        for i, msg in enumerate(messages):
            assert "role" in msg, f"Message {i} missing 'role' field"
            assert "content" in msg, f"Message {i} missing 'content' field"
            assert isinstance(
                msg["content"], list
            ), f"Message {i} content must be a list"

            for j, content_item in enumerate(msg["content"]):
                assert (
                    "type" in content_item
                ), f"Message {i} content item {j} missing 'type' field"
                if content_item["type"] == "text":
                    assert (
                        "text" in content_item
                    ), f"Message {i} content item {j} missing 'text' field"
                elif content_item["type"] == "image":
                    assert (
                        "image" in content_item
                    ), f"Message {i} content item {j} missing 'image' field"

        print(f"✓ Session messages validation passed: {len(messages)} messages")
        return True

    except Exception as e:
        print(f"✗ Session messages validation failed: {str(e)}")
        print(f"Response text: {response.text[:500]}...")
        raise


def validate_message_chronological_order(response, expected_sequence: list):
    """
    Validate that messages appear in the correct chronological order.

    Args:
        response: Tavern response object
        expected_sequence: List of expected message texts in chronological order
                          Format: ["user_msg1", "assistant_msg1", "user_msg2", "assistant_msg2"]

    Returns:
        bool: True if validation passes

    Raises:
        AssertionError: If validation fails
    """
    try:
        # Parse response data
        if hasattr(response, "json"):
            session_data = response.json()
        else:
            import json

            session_data = json.loads(response.text)

        # Check that messages field exists
        assert "messages" in session_data, "Response missing 'messages' field"
        messages = session_data["messages"]

        # Extract all message texts in order
        actual_sequence = []
        for msg in messages:
            for content_item in msg.get("content", []):
                if content_item.get("type") in ["input_text", "output_text"]:
                    actual_sequence.append(content_item.get("text", ""))

        # Check that we have the expected number of messages
        assert len(actual_sequence) == len(
            expected_sequence
        ), f"Expected {len(expected_sequence)} messages, got {len(actual_sequence)}"

        # Check each message in order
        for i, (actual, expected) in enumerate(zip(actual_sequence, expected_sequence)):
            assert (
                actual == expected
            ), f"Message {i+1}: expected '{expected}', got '{actual}'"

        print(
            f"✓ Message chronological order validation passed: {len(actual_sequence)} messages in correct order"
        )
        return True

    except Exception as e:
        print(f"✗ Message chronological order validation failed: {str(e)}")
        print(f"Response text: {response.text[:500]}...")
        raise


def validate_list_not_empty(response):
    """
    Validate that the response contains a non-empty list.

    Args:
        response: Tavern response object

    Returns:
        bool: True if validation passes

    Raises:
        AssertionError: If validation fails
    """
    try:
        if hasattr(response, "json"):
            data = response.json()
        else:
            import json

            data = json.loads(response.text)

        assert isinstance(data, list), f"Expected list, got {type(data)}"
        assert len(data) > 0, "Expected non-empty list"

        print(f"✓ List validation passed: {len(data)} items")
        return True

    except Exception as e:
        print(f"✗ List validation failed: {str(e)}")
        print(f"Response text: {response.text[:500]}...")
        raise


def validate_conversation_messages(response):
    """
    Validate that conversation messages response has non-empty messages array.

    Args:
        response: Tavern response object

    Returns:
        bool: True if validation passes

    Raises:
        AssertionError: If validation fails
    """
    try:
        if hasattr(response, "json"):
            data = response.json()
        else:
            import json

            data = json.loads(response.text)

        assert isinstance(data, dict), f"Expected dict, got {type(data)}"
        assert "messages" in data, "Response missing 'messages' field"
        assert isinstance(
            data["messages"], list
        ), f"Expected messages to be list, got {type(data['messages'])}"
        assert len(data["messages"]) > 0, "Expected non-empty messages list"

        print(
            f"✓ Conversation messages validation passed: {len(data['messages'])} messages"
        )
        return True

    except Exception as e:
        print(f"✗ Conversation messages validation failed: {str(e)}")
        print(f"Response text: {response.text[:500]}...")
        raise


def validate_suite_deployment_results(response, expected_count: int):
    """
    Validate that suite deployment results contain expected number of agents.

    Args:
        response: Tavern response object
        expected_count: Expected number of deployment results

    Returns:
        bool: True if validation passes

    Raises:
        AssertionError: If validation fails
    """
    try:
        if hasattr(response, "json"):
            results = response.json()
        else:
            import json

            results = json.loads(response.text)

        assert isinstance(results, list), f"Expected list, got {type(results)}"
        assert len(results) == int(
            expected_count
        ), f"Expected {expected_count} deployment results, got {len(results)}"

        # Check that each result has required fields
        for i, result in enumerate(results):
            assert "status" in result, f"Result {i} missing status"
            assert "agent_name" in result, f"Result {i} missing agent_name"
            assert result["status"] in [
                "success",
                "skipped",
                "error",
            ], f"Result {i} has invalid status: {result['status']}"

        success_count = sum(1 for r in results if r["status"] == "success")
        print(
            f"✓ Suite deployment validation passed: {success_count}/{len(results)} successful"
        )
        return True

    except Exception as e:
        print(f"✗ Suite deployment validation failed: {str(e)}")
        print(f"Response text: {response.text[:500]}...")
        raise


def validate_agents_grouped_by_suite(response):
    """
    Validate that agents are properly grouped by suite.

    Args:
        response: Tavern response object

    Returns:
        bool: True if validation passes

    Raises:
        AssertionError: If validation fails
    """
    try:
        if hasattr(response, "json"):
            agents = response.json()
        else:
            import json

            agents = json.loads(response.text)

        # Filter to only agents with suite metadata (ignore pre-existing agents)
        suite_agents = [agent for agent in agents if agent.get("suite_id")]

        if len(suite_agents) == 0:
            print(
                "⚠ No suite agents found (only pre-existing agents without suite metadata)"
            )
            return True

        # Check that all suite agents have proper suite metadata
        for agent in suite_agents:
            assert (
                agent.get("suite_id") is not None
            ), f"Agent {agent.get('id')} missing suite_id"
            assert (
                agent.get("suite_name") is not None
            ), f"Agent {agent.get('id')} missing suite_name"
            assert (
                agent.get("category") is not None
            ), f"Agent {agent.get('id')} missing category"

        # Group agents by suite_id and verify consistent metadata within each suite
        suites_found = {}
        for agent in suite_agents:
            suite_id = agent.get("suite_id")
            if suite_id not in suites_found:
                suites_found[suite_id] = {
                    "suite_name": agent.get("suite_name"),
                    "category": agent.get("category"),
                    "agents": [],
                }
            else:
                # Verify consistent metadata within suite
                assert suites_found[suite_id]["suite_name"] == agent.get(
                    "suite_name"
                ), f"Inconsistent suite_name for suite_id {suite_id}"
                assert suites_found[suite_id]["category"] == agent.get(
                    "category"
                ), f"Inconsistent category for suite_id {suite_id}"

            suites_found[suite_id]["agents"].append(agent.get("id"))

        print(
            f"✓ Suite grouping validation passed: {len(suite_agents)} suite agents across {len(suites_found)} suites"
        )
        return True

    except Exception as e:
        print(f"✗ Suite grouping validation failed: {str(e)}")
        print(f"Response text: {response.text[:500]}...")
        raise


def validate_categories_structure(response):
    """
    Validate that suites by category response has correct structure.

    Args:
        response: Tavern response object

    Returns:
        bool: True if validation passes

    Raises:
        AssertionError: If validation fails
    """
    try:
        if hasattr(response, "json"):
            categories = response.json()
        else:
            import json

            categories = json.loads(response.text)

        assert isinstance(categories, dict), f"Expected dict, got {type(categories)}"

        # Each category should have a list of suite IDs
        for category, suite_ids in categories.items():
            assert isinstance(
                suite_ids, list
            ), f"Category {category} should have list of suite IDs, got {type(suite_ids)}"
            assert len(suite_ids) > 0, f"Category {category} has no suites"

        print(f"✓ Categories structure validation passed: {len(categories)} categories")
        return True

    except Exception as e:
        print(f"✗ Categories structure validation failed: {str(e)}")
        print(f"Response text: {response.text[:500]}...")
        raise


def validate_categories_info_structure(response):
    """
    Validate that categories info response has correct structure.

    Args:
        response: Tavern response object

    Returns:
        bool: True if validation passes

    Raises:
        AssertionError: If validation fails
    """
    try:
        if hasattr(response, "json"):
            categories_info = response.json()
        else:
            import json

            categories_info = json.loads(response.text)

        assert isinstance(
            categories_info, dict
        ), f"Expected dict, got {type(categories_info)}"

        # Each category should have name, description, icon, suite_count
        for category, info in categories_info.items():
            assert isinstance(
                info, dict
            ), f"Category {category} info should be dict, got {type(info)}"

            required_fields = ["name", "description", "icon", "suite_count"]
            for field in required_fields:
                assert field in info, f"Category {category} missing field {field}"

            assert isinstance(
                info["suite_count"], int
            ), f"Category {category} suite_count should be int, got {type(info['suite_count'])}"
            assert (
                info["suite_count"] > 0
            ), f"Category {category} should have positive suite_count"

        print(
            f"✓ Categories info structure validation passed: {len(categories_info)} categories"
        )
        return True

    except Exception as e:
        print(f"✗ Categories info structure validation failed: {str(e)}")
        print(f"Response text: {response.text[:500]}...")
        raise


def validate_template_demo_questions(response):
    """
    Validate that template demo questions are properly structured and meaningful.

    Args:
        response: Tavern response object

    Returns:
        bool: True if validation passes

    Raises:
        AssertionError: If validation fails
    """
    try:
        if hasattr(response, "json"):
            template = response.json()
        else:
            import json

            template = json.loads(response.text)

        # Check that demo_questions exists
        assert "demo_questions" in template, "Template missing demo_questions field"

        demo_questions = template["demo_questions"]

        # Demo questions can be None or a list
        if demo_questions is not None:
            assert isinstance(
                demo_questions, list
            ), f"demo_questions should be list or None, got {type(demo_questions)}"

            if len(demo_questions) > 0:
                # Each demo question should be a non-empty string
                for i, question in enumerate(demo_questions):
                    assert isinstance(
                        question, str
                    ), f"Demo question {i} should be string, got {type(question)}"
                    assert (
                        len(question.strip()) > 0
                    ), f"Demo question {i} should not be empty"
                    assert question.endswith(
                        "?"
                    ), f"Demo question {i} should end with question mark: '{question}'"
                    assert (
                        len(question) > 10
                    ), f"Demo question {i} should be meaningful (>10 chars): '{question}'"

                print(
                    f"✓ Demo questions validation passed: {len(demo_questions)} questions"
                )
            else:
                print("✓ Demo questions validation passed: empty list (acceptable)")
        else:
            print("✓ Demo questions validation passed: None (acceptable)")

        return True

    except Exception as e:
        print(f"✗ Demo questions validation failed: {str(e)}")
        print(f"Response text: {response.text[:500]}...")
        raise


def cleanup_deployed_agents(response, base_url: str):
    """
    Delete all agents from a suite deployment response.

    This function loops through all agents in the deployment response
    and deletes them via API calls.

    Args:
        response: Tavern response object from suite deployment
        base_url: Base URL for the API (e.g., "http://localhost:8000")

    Returns:
        bool: True if cleanup succeeds
    """
    import json

    import requests

    try:
        if hasattr(response, "json"):
            results = response.json()
        else:
            results = json.loads(response.text)

        if not isinstance(results, list):
            print("⚠ Response is not a list, nothing to clean up")
            return True

        deleted_count = 0
        failed_count = 0

        for result in results:
            agent_id = result.get("agent_id")
            if not agent_id or agent_id == "nonexistent":
                continue

            try:
                delete_response = requests.delete(
                    f"{base_url}/api/v1/virtual_agents/{agent_id}",
                )
                if delete_response.status_code in [204, 404]:
                    deleted_count += 1
                else:
                    print(
                        f"⚠ Failed to delete agent {agent_id}: {delete_response.status_code}"
                    )
                    failed_count += 1
            except Exception as e:
                print(f"⚠ Error deleting agent {agent_id}: {str(e)}")
                failed_count += 1

        print(f"✓ Cleanup completed: {deleted_count} deleted, {failed_count} failed")
        return True

    except Exception as e:
        print(f"✗ Cleanup failed: {str(e)}")
        # Don't raise - cleanup failures shouldn't fail tests
        return True


def validate_user_sessions(
    response, expected_session_ids: list = None, unexpected_session_ids: list = None
):
    """
    Validate that user can only see their own sessions.

    This validator checks that the session list response contains only the expected
    sessions and does not contain sessions belonging to other users.

    Args:
        response: Tavern response object
        expected_session_ids: List of session IDs that should be present
        unexpected_session_ids: List of session IDs that should NOT be present

    Returns:
        bool: True if validation passes

    Raises:
        AssertionError: If validation fails
    """
    try:
        # Parse JSON response
        if hasattr(response, "json"):
            sessions = response.json()
        else:
            import json

            sessions = json.loads(response.text)

        # Check that response is a list
        assert isinstance(sessions, list), f"Expected list, got {type(sessions)}"

        # Extract all session IDs from response
        actual_session_ids = [session.get("id") for session in sessions]

        # Check that expected sessions are present
        if expected_session_ids:
            for expected_id in expected_session_ids:
                assert (
                    expected_id in actual_session_ids
                ), f"Expected session {expected_id} not found in response. Found: {actual_session_ids}"

        # Check that unexpected sessions are NOT present
        if unexpected_session_ids:
            for unexpected_id in unexpected_session_ids:
                assert unexpected_id not in actual_session_ids, (
                    f"Unexpected session {unexpected_id} found in response "
                    f"(should be isolated). Found: {actual_session_ids}"
                )

        print(
            f"✓ User session isolation validation passed: {len(actual_session_ids)} sessions visible to user"
        )
        return True

    except Exception as e:
        print(f"✗ User session isolation validation failed: {str(e)}")
        print(f"Response text: {response.text[:500]}...")
        raise


def validate_agent_in_list(response, expected_agent_id: str):
    """
    Validate that a specific agent appears in the agent list.

    Args:
        response: Tavern response object
        expected_agent_id: Agent ID that should be present

    Returns:
        bool: True if validation passes

    Raises:
        AssertionError: If validation fails
    """
    try:
        if hasattr(response, "json"):
            agents = response.json()
        else:
            import json

            agents = json.loads(response.text)

        assert isinstance(agents, list), f"Expected list, got {type(agents)}"

        agent_ids = [agent.get("id") for agent in agents]
        assert (
            expected_agent_id in agent_ids
        ), f"Agent {expected_agent_id} not found in list. Found: {agent_ids}"

        print(f"✓ Agent in list validation passed: agent {expected_agent_id} found")
        return True

    except Exception as e:
        print(f"✗ Agent in list validation failed: {str(e)}")
        print(f"Response text: {response.text[:500]}...")
        raise


def validate_session_count(response, min_count: int = None, max_count: int = None):
    """
    Validate that session count meets expectations.

    Args:
        response: Tavern response object
        min_count: Minimum expected session count
        max_count: Maximum expected session count

    Returns:
        bool: True if validation passes

    Raises:
        AssertionError: If validation fails
    """
    try:
        if hasattr(response, "json"):
            sessions = response.json()
        else:
            import json

            sessions = json.loads(response.text)

        assert isinstance(sessions, list), f"Expected list, got {type(sessions)}"

        actual_count = len(sessions)

        if min_count is not None:
            assert (
                actual_count >= min_count
            ), f"Expected at least {min_count} sessions, got {actual_count}"

        if max_count is not None:
            assert (
                actual_count <= max_count
            ), f"Expected at most {max_count} sessions, got {actual_count}"

        print(f"✓ Session count validation passed: {actual_count} sessions")
        return True

    except Exception as e:
        print(f"✗ Session count validation failed: {str(e)}")
        print(f"Response text: {response.text[:500]}...")
        raise


def validate_pagination_limit(response, max_count: int):
    """
    Validate that pagination limit is respected.

    Args:
        response: Tavern response object
        max_count: Maximum number of items that should be returned

    Returns:
        bool: True if validation passes

    Raises:
        AssertionError: If validation fails
    """
    try:
        if hasattr(response, "json"):
            items = response.json()
        else:
            import json

            items = json.loads(response.text)

        assert isinstance(items, list), f"Expected list, got {type(items)}"

        actual_count = len(items)
        assert (
            actual_count <= max_count
        ), f"Expected at most {max_count} items, got {actual_count}"

        print(f"✓ Pagination limit validation passed: {actual_count}/{max_count} items")
        return True

    except Exception as e:
        print(f"✗ Pagination limit validation failed: {str(e)}")
        print(f"Response text: {response.text[:500]}...")
        raise


def validate_skipped_deployment(response):
    """
    Validate that template deployment was skipped (already deployed).

    Args:
        response: Tavern response object

    Returns:
        bool: True if validation passes

    Raises:
        AssertionError: If validation fails
    """
    try:
        if hasattr(response, "json"):
            result = response.json()
        else:
            import json

            result = json.loads(response.text)

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "status" in result, "Response missing status field"
        assert result["status"] == "skipped", f"Expected status 'skipped', got '{result['status']}'"
        assert "message" in result, "Response missing message field"
        assert "already deployed" in result["message"].lower(), "Message should indicate already deployed"

        print("✓ Skipped deployment validation passed")
        return True

    except Exception as e:
        print(f"✗ Skipped deployment validation failed: {str(e)}")
        print(f"Response text: {response.text[:500]}...")
        raise
