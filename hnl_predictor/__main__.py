"""Command line interface.

    python -m hnl_predictor update [--offline] [--full]   fetch new data into data/
    python -m hnl_predictor build  [--sims N]              fit models, write site/data/*.json
    python -m hnl_predictor run    [--offline] [--full]   update + build
    python -m hnl_predictor backtest                       print backtest metrics
    python -m hnl_predictor add-factor --issue-event FILE  add a soft factor from a GitHub issue event

``update`` exits with code 0 and prints ``changed=true|false`` (also written
to $GITHUB_OUTPUT when running in GitHub Actions).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

from .paths import Paths


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="hnl_predictor")
    ap.add_argument("command", choices=["update", "build", "run", "backtest", "add-factor"])
    ap.add_argument("--offline", action="store_true", help="do not call any remote source")
    ap.add_argument("--full", action="store_true", help="force a full refresh of the current season")
    ap.add_argument("--sims", type=int, default=10000, help="Monte Carlo simulations")
    ap.add_argument("--issue-event", help="GitHub issues event JSON (add-factor)")
    ap.add_argument("--result", default="factor-result.md", help="where add-factor writes its markdown report")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    paths = Paths.default()

    if args.command in ("update", "run"):
        from .update import update
        changed = update(paths, offline=args.offline, force_full=args.full)
        print(f"changed={'true' if changed else 'false'}")
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
                fh.write(f"changed={'true' if changed else 'false'}\n")
    if args.command in ("build", "run"):
        from .build import build
        meta = build(paths, n_sims=args.sims)
        print(json.dumps({k: meta[k] for k in ("generated_at", "season", "last_result_date")}))
    if args.command == "backtest":
        from .backtest import run_backtest
        from .matches import read_matches
        from .update import load_registry
        reg = load_registry(paths)
        hnl = [m for m in read_matches(paths.matches) if m.competition == "HNL"]
        seasons = sorted({m.season for m in hnl})[1:]
        res = run_backtest(hnl, reg, seasons, keep_predictions=False)
        print(json.dumps(res.to_dict(), indent=1))
    if args.command == "add-factor":
        return _add_factor(paths, args)
    return 0


def _add_factor(paths: Paths, args) -> int:
    from .factor_issue import parse_issue_body, result_markdown, validate, write_factor
    from .update import load_registry
    event = json.loads(open(args.issue_event, encoding="utf-8").read())
    issue = event["issue"]
    reg = load_registry(paths)
    hnl_ids = {tid for tid, t in reg.teams.items() if t.country == "CRO"}
    res = validate(parse_issue_body(issue.get("body") or ""), reg, hnl_ids, issue=issue["number"])
    status = write_factor(paths.soft_factors, res.entry) if res.ok else None
    with open(args.result, "w", encoding="utf-8") as fh:
        fh.write(result_markdown(res, status))
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
            fh.write(f"ok={'true' if res.ok else 'false'}\n")
    print(json.dumps({"ok": res.ok, "status": status, "errors": res.errors, "warnings": res.warnings}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
