from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import typer

from gpvb.audit import audit_site
from gpvb.models import CrawlConfig

app = typer.Typer(
    help="Google Policy Violations Bot",
    no_args_is_help=True,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)


def _parse_bool(value: Optional[str]) -> bool:
    if value is None:
        return True
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y", "on"}:
        return True
    if normalized in {"false", "0", "no", "n", "off"}:
        return False
    raise typer.BadParameter("Expected a boolean value (true/false).")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None and ctx.args:
        typer.secho(
            "Unknown command. If you meant to run an audit, use:\n"
            "  gpvb audit --site https://example.com --out ./out --max-pages 500 "
            "--concurrency 6 --respect-robots true --user-agent \"GPVB/1.0\"\n"
            "If you recently updated the code, re-run: pip install -e .",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=2)


@app.command()
def audit(
    site: str = typer.Option(..., "--site"),
    out: Path = typer.Option(Path("./out"), "--out"),
    max_pages: int = typer.Option(500, "--max-pages"),
    max_depth: int = typer.Option(3, "--max-depth"),
    concurrency: int = typer.Option(6, "--concurrency"),
    respect_robots: str = typer.Option("true", "--respect-robots"),
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
        respect_robots=_parse_bool(respect_robots),
        user_agent=user_agent,
        include_regex=include_regex,
        exclude_regex=exclude_regex,
        ignore_querystrings=ignore_querystrings,
        rate_limit_ms=rate_limit_ms,
    )
    asyncio.run(audit_site(config))


if __name__ == "__main__":
    app()
