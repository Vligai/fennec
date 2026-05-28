"""Task 2.5: CustomRules schema load/validation tests."""

import textwrap
from pathlib import Path

import pytest
import yaml

from fennec.rules.loader import RuleValidationError, load_rules
from fennec.rules.schema import CustomRules, RuleMode, RuleScope


# ------------------------------------------------------------------ #
# Load and validation                                                  #
# ------------------------------------------------------------------ #

def test_valid_yaml_loads(tmp_path):
    rules_file = tmp_path / "custom_rules.yaml"
    rules_file.write_text(textwrap.dedent("""\
        sources:
          - pattern: "self.rpc_handler.get_payload()"
            type: user_input
        sinks:
          - pattern: "InternalORM.raw_execute()"
            type: sqli
        sanitizers:
          - pattern: "internal_security.sanitize_cmd()"
            covers: cmdi
    """))
    rules = load_rules(rules_file)
    assert len(rules.sources) == 1
    assert len(rules.sinks) == 1
    assert len(rules.sanitizers) == 1
    assert rules.sanitizers[0].pattern == "internal_security.sanitize_cmd()"


def test_missing_pattern_raises_validation_error(tmp_path):
    rules_file = tmp_path / "bad_rules.yaml"
    rules_file.write_text("sinks:\n  - type: sqli\n")  # no 'pattern'
    with pytest.raises(RuleValidationError, match="validation"):
        load_rules(rules_file)


def test_missing_file_returns_empty_rules(tmp_path):
    rules = load_rules(tmp_path / "nonexistent.yaml")
    assert rules == CustomRules()
    assert rules.sources == []
    assert rules.sinks == []
    assert rules.sanitizers == []


def test_invalid_yaml_raises_validation_error(tmp_path):
    rules_file = tmp_path / "broken.yaml"
    rules_file.write_text("sources: [unclosed")
    with pytest.raises(RuleValidationError, match="YAML"):
        load_rules(rules_file)


def test_empty_yaml_returns_empty_rules(tmp_path):
    rules_file = tmp_path / "empty.yaml"
    rules_file.write_text("")
    rules = load_rules(rules_file)
    assert rules == CustomRules()


# ------------------------------------------------------------------ #
# Scope filtering (matches_file)                                       #
# ------------------------------------------------------------------ #

def test_no_scope_matches_all_files():
    scope = RuleScope()
    assert scope.matches_file("src/anything/file.py") is True


def test_path_glob_matches():
    scope = RuleScope(paths=["src/payments/**"])
    assert scope.matches_file("src/payments/checkout.py") is True
    assert scope.matches_file("src/api/views.py") is False


def test_negation_glob_excludes_tests():
    scope = RuleScope(paths=["src/**", "!src/**/tests/**"])
    assert scope.matches_file("src/api/views.py") is True
    assert scope.matches_file("src/api/tests/test_views.py") is False


def test_multiple_positive_patterns():
    scope = RuleScope(paths=["src/payments/**", "src/auth/**"])
    assert scope.matches_file("src/payments/checkout.py") is True
    assert scope.matches_file("src/auth/login.py") is True
    assert scope.matches_file("src/api/views.py") is False


# ------------------------------------------------------------------ #
# Mode handling (is_blocking)                                          #
# ------------------------------------------------------------------ #

def test_advisory_mode_not_blocking():
    scope = RuleScope(mode=RuleMode.ADVISORY)
    from fennec.rules.schema import SanitizerRule
    rule = SanitizerRule(pattern="safe_fn()", covers="cmdi", scope=scope)
    assert rule.is_blocking() is False


def test_blocking_mode_is_blocking():
    scope = RuleScope(mode=RuleMode.BLOCKING)
    from fennec.rules.schema import SinkRule
    rule = SinkRule(pattern="dangerous()", type="sqli", scope=scope)
    assert rule.is_blocking() is True


def test_default_mode_is_advisory():
    from fennec.rules.schema import SourceRule
    rule = SourceRule(pattern="get_input()", type="user_input")
    assert rule.is_blocking() is False


# ------------------------------------------------------------------ #
# Merge functions                                                      #
# ------------------------------------------------------------------ #

def test_merge_sources_includes_custom():
    from fennec.rules.loader import merge_sources
    rules = CustomRules()
    rules.sources.append(__import__("fennec.rules.schema", fromlist=["SourceRule"]).SourceRule(
        pattern="custom_source()", type="user_input"
    ))
    sources = merge_sources(rules)
    assert "custom_source()" in sources
    assert "request.body" in sources  # built-in still present


def test_merge_sinks_includes_custom():
    from fennec.rules.loader import merge_sinks
    from fennec.rules.schema import SinkRule
    rules = CustomRules()
    rules.sinks.append(SinkRule(pattern="custom_exec()", type="cmdi"))
    sinks = merge_sinks(rules)
    assert "custom_exec()" in sinks.get("cmdi", set())
    assert "subprocess.call()" in sinks.get("cmdi", set())  # built-in


def test_advisory_exit_code_zero_when_no_findings():
    from fennec.rules.loader import advisory_exit_code
    from fennec.rules.schema import SanitizerRule, RuleScope
    rules = [SanitizerRule(pattern="safe()", covers="cmdi",
                           scope=RuleScope(mode=RuleMode.BLOCKING))]
    assert advisory_exit_code(rules, has_findings=False) == 0


def test_blocking_rule_gives_exit_code_one():
    from fennec.rules.loader import advisory_exit_code
    from fennec.rules.schema import SanitizerRule, RuleScope
    rules = [SanitizerRule(pattern="safe()", covers="cmdi",
                           scope=RuleScope(mode=RuleMode.BLOCKING))]
    assert advisory_exit_code(rules, has_findings=True) == 1
