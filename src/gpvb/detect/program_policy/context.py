from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class TextBlock:
    text: str
    x: float
    y: float
    width: float
    height: float


@dataclass
class LabelBlock(TextBlock):
    font_size: float
    opacity: float


@dataclass
class ProgramPolicyContext:
    text_blocks: List[TextBlock]
    label_blocks: List[LabelBlock]
    viewport: Dict[str, int]


def build_context(extras: Dict[str, Any], viewport: Dict[str, int]) -> ProgramPolicyContext:
    text_blocks = [
        TextBlock(
            text=block.get("text", ""),
            x=float(block.get("x", 0)),
            y=float(block.get("y", 0)),
            width=float(block.get("width", 0)),
            height=float(block.get("height", 0)),
        )
        for block in extras.get("text_blocks", [])
        if block.get("text")
    ]
    label_blocks = [
        LabelBlock(
            text=block.get("text", ""),
            x=float(block.get("x", 0)),
            y=float(block.get("y", 0)),
            width=float(block.get("width", 0)),
            height=float(block.get("height", 0)),
            font_size=float(block.get("font_size", 0)),
            opacity=float(block.get("opacity", 1)),
        )
        for block in extras.get("label_blocks", [])
        if block.get("text")
    ]
    return ProgramPolicyContext(
        text_blocks=text_blocks,
        label_blocks=label_blocks,
        viewport=viewport,
    )
