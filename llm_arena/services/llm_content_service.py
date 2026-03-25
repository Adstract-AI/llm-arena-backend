from typing import Any

from common.abstract import AbstractService


class LLMContentService(AbstractService):
    """Normalize provider message content into plain text."""

    @staticmethod
    def stringify_content(content: Any) -> str:
        """
        Normalize message content into plain text.

        Args:
            content: Raw provider or LangChain message content.

        Returns:
            str: Plain-text content.
        """
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(str(item.get("text", "")))
                elif isinstance(item, str):
                    text_parts.append(item)
            return "\n".join(part for part in text_parts if part)

        return str(content)

    @staticmethod
    def extract_response_content(content: Any) -> str:
        """
        Normalize completion content from either string or content-block formats.

        Args:
            content: Raw completion content.

        Returns:
            str: Plain-text completion content.
        """
        return LLMContentService.stringify_content(content)
