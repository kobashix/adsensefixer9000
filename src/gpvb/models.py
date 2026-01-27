from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Finding(BaseModel):
    detector: str
    severity: Severity
    message: str
    evidence: Dict[str, Any] = Field(default_factory=dict)


class AdElement(BaseModel):
    selector: str
    x: float
    y: float
    width: float
    height: float
    overlaps_clickable: bool = False
    overlaps_nav: bool = False
    overlaps_content: bool = False


class PageResult(BaseModel):
    url: str
    final_url: str
    status: int
    html: str
    text: str
    screenshot_path: Optional[str] = None
    network_summary: Dict[str, int] = Field(default_factory=dict)
    ad_elements: List[AdElement] = Field(default_factory=list)
    findings: List[Finding] = Field(default_factory=list)
    skipped_reason: Optional[str] = None


class CrawlConfig(BaseModel):
    site: str
    out_dir: str
    max_pages: int = 500
    max_depth: int = 3
    concurrency: int = 6
    respect_robots: bool = True
    user_agent: str = "GPVB/1.0"
    include_regex: Optional[str] = None
    exclude_regex: Optional[str] = None
    ignore_querystrings: bool = False
    rate_limit_ms: int = 250
    list_skipped: bool = True


@dataclass
class DuplicateCluster:
    urls: List[str]
    similarity: float


class FindingsReport(BaseModel):
    summary: Dict[str, Dict[str, int]]
    pages: List[PageResult]
    duplicates: List[DuplicateCluster]
    site: str
