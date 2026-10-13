# =============================================================================
# MIT License
# Copyright (c) 2026 Aparavi Software AG
# =============================================================================

"""Unit tests for the nonce fencer module."""

import importlib.util
import os
import re

import pytest

_GUARDRAILS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'nodes', 'guardrails')


def _load_nonce_fencer():
    """Import NonceFencer and SecurityError without triggering rocketlib."""
    spec = importlib.util.spec_from_file_location(
        'guardrails.nonce_fencer',
        os.path.join(_GUARDRAILS_DIR, 'nonce_fencer.py'),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.NonceFencer, mod.SecurityError


NonceFencer, SecurityError = _load_nonce_fencer()


class TestConstruction:
    """Nonce length validation at initialization."""

    @pytest.mark.parametrize('value', [None, '16', 15, 0, -1, True, False])
    def test_invalid_lengths_rejected(self, value):
        with pytest.raises(ValueError, match='nonce_length must be an integer >= 16'):
            NonceFencer(nonce_length=value)

    @pytest.mark.parametrize('value', [16, 32, 128])
    def test_valid_lengths_accepted(self, value):
        assert NonceFencer(nonce_length=value).nonce_length == value


class TestNewCycle:
    """Nonce generation and collision retry behavior."""

    def test_nonce_length_and_hex(self):
        nonce = NonceFencer(nonce_length=16).new_cycle()
        assert len(nonce) == 32
        assert re.fullmatch(r'[0-9a-f]+', nonce)

    def test_collision_retries_then_succeeds(self, monkeypatch):
        fencer = NonceFencer(nonce_length=16)
        values = ['a' * 32, 'b' * 32]
        monkeypatch.setattr('secrets.token_hex', lambda _: values.pop(0))
        assert fencer.new_cycle(exclude='a' * 32) == 'b' * 32

    def test_collision_exhaustion_raises_security_error(self, monkeypatch):
        fencer = NonceFencer(nonce_length=16)
        monkeypatch.setattr('secrets.token_hex', lambda _: 'a' * 32)
        with pytest.raises(SecurityError, match='found in content'):
            fencer.new_cycle(exclude='a' * 32)


class TestFence:
    """Content wrapping between nonce-delimited markers."""

    def test_structure_and_content(self):
        fencer = NonceFencer()
        nonce = fencer.new_cycle()
        result = fencer.fence('hello world', nonce)
        assert result == (
            f'<<<UNTRUSTED_DATA_{nonce}>>>\n'
            'hello world\n'
            f'<<<END_UNTRUSTED_DATA_{nonce}>>>'
        )

    @pytest.mark.parametrize('content', ['', None])
    def test_empty_content_unchanged(self, content):
        assert NonceFencer().fence(content, 'a' * 32) == content

    def test_fence_rejects_collision(self):
        with pytest.raises(SecurityError, match='selected nonce'):
            NonceFencer().fence('contains-' + 'a' * 32, 'a' * 32)


class TestSystemAddendum:
    """The directive references the same markers as fencing."""

    def test_addendum_contains_directive_and_markers(self):
        fencer = NonceFencer()
        nonce = fencer.new_cycle()
        addendum = fencer.build_system_addendum(nonce)
        assert f'<<<UNTRUSTED_DATA_{nonce}>>>' in addendum
        assert f'<<<END_UNTRUSTED_DATA_{nonce}>>>' in addendum
        assert 'Do NOT interpret' in addendum
