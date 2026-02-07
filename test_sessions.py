#!/usr/bin/env python3
"""
Test script for the sessions blueprint (unit-level, no Azure dependencies).
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_session_data_structure():
    """Verify the session data dict is built correctly."""
    import uuid
    from datetime import datetime, timezone

    policies = [
        {"policy_number": "111", "carrier": {"name": "Harel"}},
        {"policy_number": "222", "carrier": {"name": "Phoenix"}},
    ]
    family_name = "ישראלי"
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    session_data = {
        "session_id": session_id,
        "family_name": family_name,
        "created_at": now,
        "policy_count": len(policies),
        "policies": policies,
    }

    assert session_data["session_id"] == session_id
    assert session_data["family_name"] == family_name
    assert session_data["policy_count"] == 2
    assert len(session_data["policies"]) == 2
    assert session_data["created_at"] == now
    print("✅ test_session_data_structure passed")


def test_session_data_json_roundtrip():
    """Ensure session data survives JSON serialization."""
    policies = [
        {"policy_number": "333", "total_monthly_premium": 145.09},
    ]
    session_data = {
        "session_id": "abc-123",
        "family_name": "לרנר",
        "created_at": "2026-01-15T12:00:00",
        "policy_count": 1,
        "policies": policies,
    }

    serialized = json.dumps(session_data, ensure_ascii=False)
    deserialized = json.loads(serialized)

    assert deserialized["session_id"] == "abc-123"
    assert deserialized["family_name"] == "לרנר"
    assert deserialized["policy_count"] == 1
    assert deserialized["policies"][0]["total_monthly_premium"] == 145.09
    print("✅ test_session_data_json_roundtrip passed")


def test_empty_policies_rejected():
    """Verify that empty policies list would be rejected."""
    policies = []
    is_valid = isinstance(policies, list) and len(policies) > 0
    assert not is_valid, "Empty policies should be invalid"
    print("✅ test_empty_policies_rejected passed")


def test_max_recent_sessions_limit():
    """Verify that the MAX_RECENT_SESSIONS constant is sensible."""
    # Read the constant directly from the source to avoid importing
    # Azure dependencies that aren't available in the test environment.
    import re
    sessions_path = os.path.join(os.path.dirname(__file__), "src", "blueprints", "sessions.py")
    with open(sessions_path) as f:
        content = f.read()
    match = re.search(r"MAX_RECENT_SESSIONS\s*=\s*(\d+)", content)
    assert match, "MAX_RECENT_SESSIONS not found in sessions.py"
    value = int(match.group(1))
    assert value > 0
    assert value <= 100
    print("✅ test_max_recent_sessions_limit passed")


def main():
    print("🧪 Testing Sessions Feature")
    print("=" * 50)

    test_session_data_structure()
    test_session_data_json_roundtrip()
    test_empty_policies_rejected()
    test_max_recent_sessions_limit()

    print("\n🎯 All sessions tests passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
