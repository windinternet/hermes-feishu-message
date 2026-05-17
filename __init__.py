"""
hermes-feishu-message — Enhanced Feishu (Lark) messaging for Hermes Agent.

Replaces the built-in FeishuAdapter with CardKit v2 streaming cards,
one-card-per-turn consolidation, and runtime footer (model/duration/tokens/%).
"""

from .adapter import register

__all__ = ["register"]
