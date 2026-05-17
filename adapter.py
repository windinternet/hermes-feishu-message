"""
Enhanced Feishu (Lark) platform adapter with CardKit v2 streaming cards.

Subclasses the built-in ``FeishuAdapter`` and overrides:
- ``send()`` — CardKit v2 streaming cards + one-card-per-turn consolidation
- ``edit_message()`` — CardKit content-update API with typewriter effect
- ``_merge_footer_into_card()`` — runtime footer line (model · duration · tokens · %)
- ``_build_card_stream_start()`` — CardKit entity creation with streaming config
- ``_rebuild_streaming_card()`` — transparent recovery on 300309 timeout
- ``_send_final_card()`` — fallback non-streaming final card

Registers via ``platform_registry``, replacing the built-in adapter at gateway
startup ("last writer wins" — see ``gateway/platform_registry.py:178``).

Requirements
------------
- Hermes Agent with Feishu platform already configured
- ``lark-oapi`` package installed (same as built-in adapter)
- ``runtime_footer.enabled: true`` in ``config.yaml`` for the footer line
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, Optional

# ── Base adapter + helpers from the built-in Feishu module ──────────────────
from gateway.platforms.feishu import (
    FeishuAdapter as _BaseFeishuAdapter,
    _preprocess_content_for_feishu,
    _build_interactive_card_payload,
    _POST_CONTENT_INVALID_RE,
    _build_markdown_post_payload,
    _strip_markdown_to_plain_text,
)

# ── CardKit API builders (from lark-oapi) ──────────────────────────────────
try:
    from lark_oapi.api.cardkit.v1 import (
        CreateCardRequest,
        CreateCardRequestBody,
        ContentCardElementRequest,
        ContentCardElementRequestBody,
        SettingsCardRequest,
        SettingsCardRequestBody,
    )
    _CARDKIT_AVAILABLE = True
except ImportError:
    _CARDKIT_AVAILABLE = False

from gateway.platforms.base import SendResult

logger = logging.getLogger("hermes.feishu.cardkit")


# ═══════════════════════════════════════════════════════════════════════════════
# Enhanced Adapter
# ═══════════════════════════════════════════════════════════════════════════════

class FeishuCardKitAdapter(_BaseFeishuAdapter):
    """Feishu adapter with CardKit v2 streaming card support.

    Inherits everything from the built-in adapter (connect, receive, media,
    reactions, execution approval, formatting, etc.) and only overrides the
    outbound send/edit path to use CardKit streaming cards.
    """

    def __init__(self, config):
        if not _CARDKIT_AVAILABLE:
            raise ImportError(
                "lark-oapi CardKit v1 API not available. "
                "Ensure lark-oapi is installed: pip install lark-oapi"
            )
        super().__init__(config)

        # ── CardKit streaming state ─────────────────────────────────────────
        self._card_streams: Dict[str, Dict[str, Any]] = {}
        self._chat_active_card: Dict[str, str] = {}
        self._chat_response_buf: Dict[str, str] = {}
        self._chat_tool_lines: Dict[str, str] = {}

    # ── Content merging ─────────────────────────────────────────────────────
    def _get_merged_content(self, chat_id: str) -> str:
        """Merge response text and tool-progress lines into one card body."""
        parts = []
        resp = self._chat_response_buf.get(chat_id, "")
        if resp:
            parts.append(resp)
        tool = self._chat_tool_lines.get(chat_id, "")
        if tool:
            parts.append(tool)
        return "\n\n".join(parts)

    # ═════════════════════════════════════════════════════════════════════════
    # send() — CardKit streaming + one-card-per-turn
    # ═════════════════════════════════════════════════════════════════════════

    async def send(
        self,
        chat_id: str,
        content: str,
        reply_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SendResult:
        """Send a Feishu message via CardKit v2 streaming card.

        One card per turn: first send creates the card, subsequent sends
        update it, footer merges in with completion metadata.
        """
        if not self._client:
            return SendResult(success=False, error="Not connected")

        formatted = self.format_message(content)

        # Heuristic: content with runtime footer → final (non-streaming)
        has_footer = any(
            indicator in formatted
            for indicator in (" · ", "tokens", "context", "% ", "K ")
        )

        # ── Footer-only: short footer line after streaming body delivered ──
        if has_footer and len(formatted) < 200 and self._card_streams:
            await self._merge_footer_into_card(formatted)
            return SendResult(success=True)

        # ── Active card routing: update existing card ──
        active_msg_id = self._chat_active_card.get(chat_id)
        if active_msg_id and self._card_streams.get(active_msg_id):
            buf = self._chat_response_buf.get(chat_id, "")
            if buf:
                buf += "\n\n" + formatted
            else:
                buf = formatted
            self._chat_response_buf[chat_id] = buf
            merged = self._get_merged_content(chat_id)
            return await self.edit_message(
                chat_id=chat_id,
                message_id=active_msg_id,
                content=merged,
                finalize=False,
            )

        # ── First message: create a new CardKit streaming card ──
        chunks = self.truncate_message(formatted, self.MAX_MESSAGE_LENGTH)
        last_response = None

        is_streaming = not has_footer
        status = "生成中..." if is_streaming else "已完成"

        self._chat_response_buf[chat_id] = formatted

        try:
            for chunk in chunks:
                if is_streaming:
                    msg_type, payload = self._build_card_stream_start(
                        chunk, status=status
                    )
                else:
                    msg_type, payload = self._build_outbound_payload(
                        chunk, status=status, extract_footer=True,
                    )

                try:
                    response = await self._feishu_send_with_retry(
                        chat_id=chat_id, msg_type=msg_type, payload=payload,
                        reply_to=reply_to, metadata=metadata,
                    )
                except Exception as exc:
                    if msg_type == "interactive":
                        logger.warning(
                            "[Feishu] Interactive card rejected; falling back to post: %s",
                            str(exc)[:200],
                        )
                        response = await self._feishu_send_with_retry(
                            chat_id=chat_id, msg_type="post",
                            payload=_build_markdown_post_payload(chunk),
                            reply_to=reply_to, metadata=metadata,
                        )
                    elif msg_type != "post" or not _POST_CONTENT_INVALID_RE.search(str(exc)):
                        raise
                    else:
                        logger.warning("[Feishu] Invalid post; falling back to plain text")
                        response = await self._feishu_send_with_retry(
                            chat_id=chat_id, msg_type="text",
                            payload=json.dumps(
                                {"text": _strip_markdown_to_plain_text(chunk)},
                                ensure_ascii=False,
                            ),
                            reply_to=reply_to, metadata=metadata,
                        )

                if (
                    msg_type == "post"
                    and not self._response_succeeded(response)
                    and _POST_CONTENT_INVALID_RE.search(
                        str(getattr(response, "msg", "") or "")
                    )
                ):
                    logger.warning("[Feishu] Post rejected; falling back to plain text")
                    response = await self._feishu_send_with_retry(
                        chat_id=chat_id, msg_type="text",
                        payload=json.dumps(
                            {"text": _strip_markdown_to_plain_text(chunk)},
                            ensure_ascii=False,
                        ),
                        reply_to=reply_to, metadata=metadata,
                    )

                last_response = response

                # Re-key pending CardKit entry → actual message_id
                pending = self._card_streams.pop("__pending__", None)
                if pending and is_streaming:
                    message_id = self._extract_response_field(response, "message_id")
                    if message_id:
                        mid_str = str(message_id)
                        self._card_streams[mid_str] = pending
                        self._chat_active_card[chat_id] = mid_str

            return self._finalize_send_result(last_response, "send failed")

        except Exception as exc:
            logger.error("[Feishu] Send error: %s", exc, exc_info=True)
            return SendResult(success=False, error=str(exc))

    # ═════════════════════════════════════════════════════════════════════════
    # edit_message() — CardKit content-update API
    # ═════════════════════════════════════════════════════════════════════════

    async def edit_message(
        self,
        chat_id: str,
        message_id: str,
        content: str,
        *,
        finalize: bool = False,
    ) -> SendResult:
        """Edit a streaming card via CardKit content-update API."""
        if not self._client:
            return SendResult(success=False, error="Not connected")

        stream = self._card_streams.get(message_id)
        if not stream:
            logger.warning(
                "[Feishu] No CardKit stream for msg=%s, fallback to inline edit",
                message_id,
            )
            return await self._edit_message_inline(
                chat_id, message_id, content, finalize=finalize
            )

        card_id = stream["card_id"]
        element_id = stream["element_id"]

        # Merge tool-progress with response text
        resp_buf = self._chat_response_buf.get(chat_id, "")
        merged_from_buf = self._get_merged_content(chat_id)
        if content.strip() == merged_from_buf.strip():
            merged = content
        elif resp_buf and content.strip():
            self._chat_tool_lines[chat_id] = content
            merged = self._get_merged_content(chat_id)
        else:
            merged = content

        body = _preprocess_content_for_feishu(merged)
        if finalize:
            full_content = body
        else:
            full_content = f"{body}\n---\n生成中..."

        try:
            # Step 1: Push updated content
            stream["sequence"] += 1
            content_body = (
                ContentCardElementRequestBody.builder()
                .content(full_content)
                .uuid(str(uuid.uuid4()))
                .sequence(stream["sequence"])
                .build()
            )
            content_request = (
                ContentCardElementRequest.builder()
                .card_id(card_id)
                .element_id(element_id)
                .request_body(content_body)
                .build()
            )
            response = await asyncio.to_thread(
                self._client.cardkit.v1.card_element.content, content_request,
            )

            if finalize:
                stream["sequence"] += 1
                settings = json.dumps(
                    {"config": {"streaming_mode": False}}, ensure_ascii=False
                )
                settings_body = (
                    SettingsCardRequestBody.builder()
                    .settings(settings)
                    .uuid(str(uuid.uuid4()))
                    .sequence(stream["sequence"])
                    .build()
                )
                settings_request = (
                    SettingsCardRequest.builder()
                    .card_id(card_id)
                    .request_body(settings_body)
                    .build()
                )
                await asyncio.to_thread(
                    self._client.cardkit.v1.card.settings, settings_request,
                )

            if self._response_succeeded(response):
                return SendResult(success=True, message_id=message_id)
            else:
                code = getattr(response, "code", "unknown")
                msg = getattr(response, "msg", "unknown")
                if code == 300309 and not finalize:
                    logger.info(
                        "[Feishu] Streaming card timed out for msg=%s, rebuilding",
                        message_id,
                    )
                    self._card_streams.pop(message_id, None)
                    self._chat_active_card.pop(chat_id, None)
                    rebuilt = await self._rebuild_streaming_card(
                        chat_id=chat_id, content=content,
                    )
                    if rebuilt.success:
                        return rebuilt
                logger.warning(
                    "[Feishu] CardKit content update failed: [%s] %s", code, msg
                )
                return SendResult(
                    success=False, error=f"[{code}] {msg}", message_id=message_id,
                )
        except Exception as exc:
            logger.error(
                "[Feishu] CardKit edit error for msg=%s: %s",
                message_id, exc, exc_info=True,
            )
            return SendResult(success=False, error=str(exc))

    # ═════════════════════════════════════════════════════════════════════════
    # _build_card_stream_start() — CardKit entity creation
    # ═════════════════════════════════════════════════════════════════════════

    def _build_card_stream_start(self, chunk: str, *, status: str) -> tuple:
        """Create a CardKit card entity with streaming_mode enabled."""
        element_id = "content_1"
        body = _preprocess_content_for_feishu(chunk)
        full_content = f"{body}\n---\n{status}"

        card_json = {
            "schema": "2.0",
            "config": {
                "wide_screen_mode": True,
                "streaming_mode": True,
                "update_multi": True,
                "streaming_config": {
                    "print_frequency_ms": {
                        "default": 30, "android": 30, "ios": 30, "pc": 30
                    },
                    "print_step": {
                        "default": 3, "android": 3, "ios": 3, "pc": 3
                    },
                    "print_strategy": "fast",
                },
            },
            "body": {
                "elements": [
                    {
                        "tag": "markdown",
                        "content": full_content,
                        "element_id": element_id,
                    }
                ]
            },
        }
        card_json_str = json.dumps(card_json, ensure_ascii=False)

        create_body = (
            CreateCardRequestBody.builder()
            .type("card_json")
            .data(card_json_str)
            .build()
        )
        create_request = (
            CreateCardRequest.builder().request_body(create_body).build()
        )
        create_response = self._client.cardkit.v1.card.create(create_request)

        if not self._response_succeeded(create_response):
            err = getattr(create_response, "msg", "unknown")
            logger.error("[Feishu] CardKit create card failed: %s", err)
            raise RuntimeError(f"CardKit create card failed: {err}")

        card_id = getattr(create_response.data, "card_id", None)
        if not card_id:
            raise RuntimeError("CardKit create card returned no card_id")

        card_ref = {"type": "card", "data": {"card_id": card_id}}
        payload = json.dumps(card_ref, ensure_ascii=False)

        self._card_streams["__pending__"] = {
            "card_id": card_id,
            "element_id": element_id,
            "sequence": 0,
        }
        logger.info(
            "[Feishu] CardKit stream created: card_id=%s element_id=%s",
            card_id, element_id,
        )
        return "interactive", payload

    # ═════════════════════════════════════════════════════════════════════════
    # Footer merge
    # ═════════════════════════════════════════════════════════════════════════

    async def _merge_footer_into_card(self, footer_text: str) -> None:
        """Merge runtime footer into the most recent streaming card."""
        entry = None
        for msg_id, stream in reversed(list(self._card_streams.items())):
            if msg_id == "__pending__":
                continue
            entry = (msg_id, stream)
            break

        if entry is None:
            logger.debug("[Feishu] No active CardKit stream to merge footer into")
            return

        msg_id, stream = entry
        card_id = stream["card_id"]
        element_id = stream["element_id"]

        chat_id = None
        for cid, mid in self._chat_active_card.items():
            if mid == msg_id:
                chat_id = cid
                break

        buf = self._get_merged_content(chat_id or "")
        if buf:
            body = _preprocess_content_for_feishu(buf)
            merged = f"{body}\n\n已完成 · {footer_text}"
        else:
            merged = f"已完成 · {footer_text}"

        try:
            stream["sequence"] += 1
            content_body = (
                ContentCardElementRequestBody.builder()
                .content(merged)
                .uuid(str(uuid.uuid4()))
                .sequence(stream["sequence"])
                .build()
            )
            content_request = (
                ContentCardElementRequest.builder()
                .card_id(card_id)
                .element_id(element_id)
                .request_body(content_body)
                .build()
            )
            response = await asyncio.to_thread(
                self._client.cardkit.v1.card_element.content, content_request,
            )

            if not self._response_succeeded(response):
                code = getattr(response, "code", "?")
                if code == 300309:
                    self._card_streams.pop(msg_id, None)
                    if chat_id:
                        self._chat_active_card.pop(chat_id, None)
                        self._chat_response_buf.pop(chat_id, None)
                        self._chat_tool_lines.pop(chat_id, None)
                    await self._send_final_card(chat_id or "", merged, footer_text)
                    return

            stream["sequence"] += 1
            settings = json.dumps(
                {"config": {"streaming_mode": False}}, ensure_ascii=False
            )
            settings_body = (
                SettingsCardRequestBody.builder()
                .settings(settings)
                .uuid(str(uuid.uuid4()))
                .sequence(stream["sequence"])
                .build()
            )
            settings_request = (
                SettingsCardRequest.builder()
                .card_id(card_id)
                .request_body(settings_body)
                .build()
            )
            await asyncio.to_thread(
                self._client.cardkit.v1.card.settings, settings_request,
            )

            logger.info(
                "[Feishu] Footer merged + streaming closed: %s · %s",
                card_id, footer_text[:60],
            )
        except Exception as exc:
            logger.warning("[Feishu] Footer merge error: %s", exc)
        finally:
            self._card_streams.pop(msg_id, None)
            if chat_id:
                self._chat_active_card.pop(chat_id, None)
                self._chat_response_buf.pop(chat_id, None)
                self._chat_tool_lines.pop(chat_id, None)

    # ═════════════════════════════════════════════════════════════════════════
    # Recovery helpers
    # ═════════════════════════════════════════════════════════════════════════

    async def _rebuild_streaming_card(
        self, chat_id: str, content: str,
    ) -> SendResult:
        """Rebuild a streaming card when the original stream timed out."""
        try:
            body = _preprocess_content_for_feishu(content)
            full_content = f"{body}\n---\n生成中..."
            element_id = "content_1"

            card_json = {
                "schema": "2.0",
                "config": {
                    "wide_screen_mode": True,
                    "streaming_mode": True,
                    "update_multi": True,
                    "streaming_config": {
                        "print_frequency_ms": {
                            "default": 30, "android": 30, "ios": 30, "pc": 30
                        },
                        "print_step": {
                            "default": 3, "android": 3, "ios": 3, "pc": 3
                        },
                        "print_strategy": "fast",
                    },
                },
                "body": {
                    "elements": [
                        {
                            "tag": "markdown",
                            "content": full_content,
                            "element_id": element_id,
                        }
                    ]
                },
            }
            card_json_str = json.dumps(card_json, ensure_ascii=False)

            create_body = (
                CreateCardRequestBody.builder()
                .type("card_json")
                .data(card_json_str)
                .build()
            )
            create_request = (
                CreateCardRequest.builder().request_body(create_body).build()
            )
            create_response = await asyncio.to_thread(
                self._client.cardkit.v1.card.create, create_request,
            )

            if not self._response_succeeded(create_response):
                return SendResult(
                    success=False,
                    error=str(getattr(create_response, "msg", "CardKit create failed")),
                )

            card_id = getattr(create_response.data, "card_id", None)
            if not card_id:
                return SendResult(success=False, error="CardKit create returned no card_id")

            card_ref = {"type": "card", "data": {"card_id": card_id}}
            payload = json.dumps(card_ref, ensure_ascii=False)
            response = await self._feishu_send_with_retry(
                chat_id=chat_id, msg_type="interactive", payload=payload,
                reply_to=None, metadata=None,
            )

            message_id = self._extract_response_field(response, "message_id")
            if not message_id:
                return SendResult(success=False, error="No message_id in rebuild response")

            mid_str = str(message_id)
            self._card_streams[mid_str] = {
                "card_id": card_id, "element_id": element_id, "sequence": 0,
            }
            self._chat_active_card[chat_id] = mid_str
            self._chat_response_buf[chat_id] = content
            self._chat_tool_lines.pop(chat_id, None)

            logger.info(
                "[Feishu] Stream rebuild: new card_id=%s msg_id=%s (%d chars)",
                card_id, mid_str, len(content),
            )
            return SendResult(success=True, message_id=message_id)

        except Exception as exc:
            logger.error("[Feishu] Rebuild streaming card failed: %s", exc, exc_info=True)
            return SendResult(success=False, error=str(exc))

    async def _send_final_card(
        self, chat_id: str, content: str, footer_text: str,
    ) -> None:
        """Send a non-streaming interactive card with final content + footer."""
        try:
            body = _preprocess_content_for_feishu(content)
            payload = _build_interactive_card_payload(body)
            await self._feishu_send_with_retry(
                chat_id=chat_id, msg_type="interactive", payload=payload,
                reply_to=None, metadata=None,
            )
            logger.info(
                "[Feishu] Final card sent (%d chars): %s",
                len(content), footer_text[:60],
            )
        except Exception as exc:
            logger.error("[Feishu] Final card send failed: %s", exc)


# ═══════════════════════════════════════════════════════════════════════════════
# Plugin Registration
# ═══════════════════════════════════════════════════════════════════════════════

def _check_requirements() -> bool:
    if not _CARDKIT_AVAILABLE:
        logger.warning("lark-oapi CardKit v1 not available")
        return False
    return True


def register(ctx) -> None:
    """Plugin entry point — registers as 'feishu', overriding the built-in adapter."""
    ctx.register_platform(
        name="feishu",
        label="Feishu (CardKit Enhanced)",
        adapter_factory=lambda cfg: FeishuCardKitAdapter(cfg),
        check_fn=_check_requirements,
        validate_config=None,
        required_env=["FEISHU_APP_ID", "FEISHU_APP_SECRET"],
        install_hint="pip install lark-oapi",
        allowed_users_env="FEISHU_ALLOWED_USERS",
        allow_all_env="FEISHU_ALLOW_ALL_USERS",
        emoji="🐦",
        allow_update_command=True,
        platform_hint=(
            "You are on Feishu (Lark) with CardKit v2 streaming cards. "
            "Markdown IS fully supported — use headings, bold, italic, "
            "code blocks, tables, and links. All messages for a single "
            "turn appear inside ONE card. A runtime footer (模型 · 耗时 · "
            "tokens · 上下文%) is appended to the final card. "
            "Images render inline; include MEDIA:/absolute/path in your "
            "response to attach files."
        ),
        cron_deliver_env_var="FEISHU_HOME_CHANNEL",
    )
