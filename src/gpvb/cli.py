from __future__ import annotations

import asyncio
from pathlib import Path

import typer

from gpvb.audit import audit_site
from gpvb.models import CrawlConfig

app = typer.Typer(help="Google Policy Violations Bot")


@app.command()
def audit(
    site: str = typer.Option(..., "--site"),
    out: Path = typer.Option(Path("./out"), "--out"),
    max_pages: int = typer.Option(500, "--max-pages"),
    max_depth: int = typer.Option(3, "--max-depth"),
    concurrency: int = typer.Option(6, "--concurrency"),
    respect_robots: bool = typer.Option(True, "--respect-robots"),
    user_agent: str = typer.Option("GPVB/1.0", "--user-agent"),
    include_regex: str = typer.Option(None, "--include-regex"),
    exclude_regex: str = typer.Option(None, "--exclude-regex"),
    ignore_querystrings: bool = typer.Option(False, "--ignore-querystrings"),
    rate_limit_ms: int = typer.Option(250, "--rate-limit-ms"),
) -> None:
    config = CrawlConfig(
        site=site,
        out_dir=str(out),
        max_pages=max_pages,
        max_depth=max_depth,
        concurrency=concurrency,
        respect_robots=respect_robots,
        user_agent=user_agent,
        include_regex=include_regex,
        exclude_regex=exclude_regex,
        ignore_querystrings=ignore_querystrings,
        rate_limit_ms=rate_limit_ms,
    )
    asyncio.run(audit_site(config))


if __name__ == "__main__":
    app()
