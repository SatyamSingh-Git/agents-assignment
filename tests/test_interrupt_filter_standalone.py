"""
Truly standalone test for InterruptFilter.
This imports the module file directly using importlib to bypass the package __init__.py chain.
"""

import importlib.util
import os
import sys

# Get absolute path to the interrupt_filter.py file
current_dir = os.path.dirname(os.path.abspath(__file__))
module_path = os.path.join(
    current_dir, "..", "livekit-agents", "livekit", "agents", "voice", "interrupt_filter.py"
)
module_path = os.path.normpath(module_path)

# Load the module directly without going through package imports
# Important: We need to add the module to sys.modules BEFORE exec_module
# so that dataclasses can find the module context
spec = importlib.util.spec_from_file_location("interrupt_filter", module_path)
interrupt_filter = importlib.util.module_from_spec(spec)
sys.modules["interrupt_filter"] = interrupt_filter  # Fix for dataclass compatibility
spec.loader.exec_module(interrupt_filter)

# Get the classes from the loaded module
InterruptFilter = interrupt_filter.InterruptFilter
InterruptFilterConfig = interrupt_filter.InterruptFilterConfig


def test_default_config():
    """Test that default config has expected ignore and command words."""
    config = InterruptFilterConfig()
    filter = InterruptFilter(config)

    assert filter.enabled is True
    assert "yeah" in filter.config.ignore_words
    assert "ok" in filter.config.ignore_words
    assert "stop" in filter.config.command_words
    assert "wait" in filter.config.command_words
    print("✓ test_default_config passed")


def test_should_ignore_filler_words_while_speaking():
    """Test that filler words are ignored when agent is speaking."""
    filter = InterruptFilter()

    # Single filler words
    assert filter.should_ignore("yeah", agent_is_speaking=True) is True
    assert filter.should_ignore("ok", agent_is_speaking=True) is True
    assert filter.should_ignore("hmm", agent_is_speaking=True) is True
    assert filter.should_ignore("uh-huh", agent_is_speaking=True) is True
    assert filter.should_ignore("right", agent_is_speaking=True) is True
    assert filter.should_ignore("mhm", agent_is_speaking=True) is True

    # Multiple filler words
    assert filter.should_ignore("yeah ok", agent_is_speaking=True) is True
    assert filter.should_ignore("ok ok ok", agent_is_speaking=True) is True
    print("✓ test_should_ignore_filler_words_while_speaking passed")


def test_should_not_ignore_filler_words_while_silent():
    """Test that filler words are NOT ignored when agent is silent."""
    filter = InterruptFilter()

    # When agent is NOT speaking - should NOT ignore
    assert filter.should_ignore("yeah", agent_is_speaking=False) is False
    assert filter.should_ignore("ok", agent_is_speaking=False) is False
    assert filter.should_ignore("hmm", agent_is_speaking=False) is False
    print("✓ test_should_not_ignore_filler_words_while_silent passed")


def test_command_words_interrupt():
    """Test that command words trigger interruption even when speaking."""
    filter = InterruptFilter()

    # Command words should never be ignored
    assert filter.should_ignore("stop", agent_is_speaking=True) is False
    assert filter.should_ignore("wait", agent_is_speaking=True) is False
    assert filter.should_ignore("no", agent_is_speaking=True) is False
    assert filter.should_ignore("hold on", agent_is_speaking=True) is False
    assert filter.should_ignore("be quiet", agent_is_speaking=True) is False
    print("✓ test_command_words_interrupt passed")


def test_mixed_input_with_command():
    """Test that mixed input containing command words is not ignored."""
    filter = InterruptFilter()

    # Mixed input with command word should NOT be ignored
    assert filter.should_ignore("yeah okay but wait", agent_is_speaking=True) is False
    assert filter.should_ignore("ok stop", agent_is_speaking=True) is False
    assert filter.should_ignore("hmm no", agent_is_speaking=True) is False
    print("✓ test_mixed_input_with_command passed")


def test_real_sentences_interrupt():
    """Test that real sentences (not just filler) cause interruption."""
    filter = InterruptFilter()

    # Full sentences should not be ignored
    assert filter.should_ignore("I have a question", agent_is_speaking=True) is False
    assert filter.should_ignore("What about the weather", agent_is_speaking=True) is False
    assert filter.should_ignore("Tell me more", agent_is_speaking=True) is False
    print("✓ test_real_sentences_interrupt passed")


def test_case_insensitivity():
    """Test that filtering is case-insensitive."""
    filter = InterruptFilter()

    assert filter.should_ignore("YEAH", agent_is_speaking=True) is True
    assert filter.should_ignore("Yeah", agent_is_speaking=True) is True
    assert filter.should_ignore("OK", agent_is_speaking=True) is True
    assert filter.should_ignore("STOP", agent_is_speaking=True) is False
    print("✓ test_case_insensitivity passed")


def test_classify_input():
    """Test the classify_input method."""
    filter = InterruptFilter()

    # Agent speaking
    assert filter.classify_input("yeah", agent_is_speaking=True) == "ignore"
    assert filter.classify_input("stop", agent_is_speaking=True) == "interrupt"
    assert filter.classify_input("what time is it", agent_is_speaking=True) == "interrupt"

    # Agent silent
    assert filter.classify_input("yeah", agent_is_speaking=False) == "respond"
    assert filter.classify_input("stop", agent_is_speaking=False) == "respond"
    print("✓ test_classify_input passed")


def test_disabled_filter():
    """Test that disabled filter never ignores."""
    config = InterruptFilterConfig(enabled=False)
    filter = InterruptFilter(config)

    assert filter.enabled is False
    assert filter.should_ignore("yeah", agent_is_speaking=True) is False
    print("✓ test_disabled_filter passed")


# Integration scenarios matching the assignment requirements
def test_scenario_1_agent_explaining():
    """Scenario 1: Agent is explaining, user says 'yeah', 'ok', 'uh-huh'."""
    filter = InterruptFilter()
    
    responses = ["yeah", "ok", "uh-huh", "right", "mhm"]
    for response in responses:
        assert filter.should_ignore(response, agent_is_speaking=True) is True, (
            f"Expected '{response}' to be ignored while agent speaking"
        )
    print("✓ Scenario 1: Agent ignores filler words while speaking")


def test_scenario_2_agent_asks_question():
    """Scenario 2: Agent asks question, user responds with 'yeah'."""
    filter = InterruptFilter()
    
    # Agent is NOT speaking (waiting for answer)
    assert filter.should_ignore("yeah", agent_is_speaking=False) is False
    assert filter.classify_input("yeah", agent_is_speaking=False) == "respond"
    print("✓ Scenario 2: Agent responds to 'yeah' when silent")


def test_scenario_3_user_says_stop():
    """Scenario 3: Agent speaking, user says 'stop'."""
    filter = InterruptFilter()
    
    # Should NOT be ignored - agent should stop
    assert filter.should_ignore("stop", agent_is_speaking=True) is False
    assert filter.classify_input("stop", agent_is_speaking=True) == "interrupt"
    print("✓ Scenario 3: Agent stops immediately for 'stop'")


def test_scenario_4_mixed_input():
    """Scenario 4: User says 'Yeah okay but wait'."""
    filter = InterruptFilter()
    
    # Contains 'wait' command word - should NOT be ignored
    assert filter.should_ignore("yeah okay but wait", agent_is_speaking=True) is False
    assert filter.classify_input("yeah okay but wait", agent_is_speaking=True) == "interrupt"
    print("✓ Scenario 4: Agent stops for 'Yeah okay but wait'")


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("Running InterruptFilter Tests")
    print("="*60 + "\n")
    
    tests = [
        test_default_config,
        test_should_ignore_filler_words_while_speaking,
        test_should_not_ignore_filler_words_while_silent,
        test_command_words_interrupt,
        test_mixed_input_with_command,
        test_real_sentences_interrupt,
        test_case_insensitivity,
        test_classify_input,
        test_disabled_filter,
    ]
    
    print("Unit Tests:")
    print("-" * 40)
    for test in tests:
        test()
    
    print("\n" + "-"*40)
    print("Assignment Scenario Tests:")
    print("-" * 40)
    test_scenario_1_agent_explaining()
    test_scenario_2_agent_asks_question()
    test_scenario_3_user_says_stop()
    test_scenario_4_mixed_input()
    
    print("\n" + "="*60)
    print("ALL TESTS PASSED! ✓")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_all_tests()
