#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from dataclasses import asdict
from dataclasses import dataclass


def git(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        stderr = result.stderr.strip()
        raise SystemExit(stderr or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def git_ok(*args: str) -> bool:
    result = subprocess.run(
        ["git", *args],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


@dataclass(frozen=True)
class BranchMove:
    branch: str
    old_sha: str
    new_sha: str
    distance_from_tip: int


@dataclass(frozen=True)
class RestackPlan:
    base: str
    tip: str
    old_tip_rev: str
    old_tip_sha: str
    new_tip_sha: str
    old_anchor_sha: str | None
    new_anchor_sha: str | None
    moves: list[BranchMove]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Restack local branch refs after rebasing the tip branch of a linear stack. "
            "Default mode is a dry run that only prints the inferred mapping."
        )
    )
    parser.add_argument(
        "--base",
        default="main",
        help="Base branch name. Defaults to 'main'.",
    )
    parser.add_argument(
        "--tip",
        default=None,
        help="Tip branch name. Defaults to the currently checked out branch.",
    )
    parser.add_argument(
        "--old-tip",
        default=None,
        help="Old pre-rebase tip revision. Defaults to '<tip>@{1}'.",
    )
    parser.add_argument(
        "--remote",
        default="origin",
        help="Remote used by --push. Defaults to 'origin'.",
    )
    parser.add_argument(
        "--match-prefix",
        action="append",
        default=[],
        metavar="PREFIX",
        help=(
            "Only consider stacked branches whose names start with PREFIX. "
            "Repeat to allow multiple prefixes."
        ),
    )
    parser.add_argument(
        "--range-diff",
        action="store_true",
        help=(
            "Show `git range-diff` for the inferred stack rewrite before applying any ref moves."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the inferred plan as JSON.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the inferred plan without moving refs. This is the default behavior.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Move local branch refs to the inferred rebased commits.",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Force-push the updated refs after applying them. Implies --apply.",
    )
    return parser.parse_args()


def current_branch() -> str:
    branch = git("symbolic-ref", "--quiet", "--short", "HEAD")
    if not branch:
        raise SystemExit("Detached HEAD is not supported for auto-detecting the tip branch.")
    return branch


def first_parent_chain(tip_sha: str) -> list[str]:
    chain = git("rev-list", "--first-parent", tip_sha).splitlines()
    if not chain:
        raise SystemExit(f"Could not read first-parent history for {tip_sha}.")
    return chain


def branch_refs() -> list[tuple[str, str]]:
    rows = git("for-each-ref", "refs/heads", "--format=%(refname:short)\t%(objectname)").splitlines()
    refs: list[tuple[str, str]] = []
    for row in rows:
        branch, sha = row.split("\t", 1)
        refs.append((branch, sha))
    return refs


def include_branch(branch: str, prefixes: list[str]) -> bool:
    if not prefixes:
        return True
    return any(branch.startswith(prefix) for prefix in prefixes)


def infer_plan(base: str, tip: str, old_tip_rev: str, match_prefixes: list[str]) -> RestackPlan:
    new_tip_sha = git("rev-parse", tip)
    old_tip_sha = git("rev-parse", old_tip_rev)
    old_chain = first_parent_chain(old_tip_sha)
    old_chain_set = set(old_chain)

    candidates: list[tuple[str, str, int]] = []
    for branch, sha in branch_refs():
        if branch in {base, tip}:
            continue
        if not include_branch(branch, match_prefixes):
            continue
        if sha not in old_chain_set:
            continue
        if not git_ok("merge-base", "--is-ancestor", sha, old_tip_sha):
            continue
        distance = int(git("rev-list", "--first-parent", "--count", f"{sha}..{old_tip_sha}"))
        candidates.append((branch, sha, distance))

    if not candidates:
        prefix_suffix = ""
        if match_prefixes:
            prefix_suffix = f" matching prefixes {match_prefixes}"
        raise SystemExit(
            f"No stacked branch refs found on the old {tip} first-parent chain ({old_tip_sha[:12]}){prefix_suffix}."
        )

    groups: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for branch, sha, distance in candidates:
        groups[sha].append((branch, distance))

    ordered_groups = sorted(
        groups.items(),
        key=lambda item: item[1][0][1],
        reverse=True,
    )

    max_distance = ordered_groups[0][1][0][1]
    new_chain = first_parent_chain(new_tip_sha)
    if max_distance >= len(new_chain):
        raise SystemExit(
            f"New tip {new_tip_sha[:12]} does not have enough first-parent history for distance {max_distance}."
        )

    moves: list[BranchMove] = []
    previous_distance: int | None = None
    for old_sha, branch_entries in ordered_groups:
        distance = branch_entries[0][1]
        if previous_distance is not None and distance >= previous_distance:
            raise SystemExit("Inferred branch stack is not strictly ordered by ancestry.")
        previous_distance = distance
        new_sha = new_chain[distance]
        for branch, _ in sorted(branch_entries):
            if branch == tip and old_sha == old_tip_sha:
                continue
            if git("rev-parse", branch) == new_sha:
                continue
            moves.append(
                BranchMove(
                    branch=branch,
                    old_sha=old_sha,
                    new_sha=new_sha,
                    distance_from_tip=distance,
                )
            )

    if not moves:
        raise SystemExit("All inferred branch refs already point at the rebased commits.")

    old_anchor_sha = old_chain[max_distance + 1] if max_distance + 1 < len(old_chain) else None
    new_anchor_sha = new_chain[max_distance + 1] if max_distance + 1 < len(new_chain) else None

    return RestackPlan(
        base=base,
        tip=tip,
        old_tip_rev=old_tip_rev,
        old_tip_sha=old_tip_sha,
        new_tip_sha=new_tip_sha,
        old_anchor_sha=old_anchor_sha,
        new_anchor_sha=new_anchor_sha,
        moves=moves,
    )


def print_plan(plan: RestackPlan) -> None:
    print(f"Base branch: {plan.base}")
    print(f"Old {plan.tip} tip: {plan.old_tip_sha[:12]} ({plan.old_tip_rev})")
    print(f"New {plan.tip} tip: {plan.new_tip_sha[:12]}")
    print("Planned branch updates:")
    for move in plan.moves:
        print(
            f"  {move.branch}: {move.old_sha[:12]} -> {move.new_sha[:12]}"
            f" (distance {move.distance_from_tip} from {plan.tip})"
        )


def print_json(plan: RestackPlan) -> None:
    payload = {
        "base": plan.base,
        "tip": plan.tip,
        "old_tip_rev": plan.old_tip_rev,
        "old_tip_sha": plan.old_tip_sha,
        "new_tip_sha": plan.new_tip_sha,
        "old_anchor_sha": plan.old_anchor_sha,
        "new_anchor_sha": plan.new_anchor_sha,
        "moves": [asdict(move) for move in plan.moves],
    }
    print(json.dumps(payload, indent=2))


def show_range_diff(plan: RestackPlan) -> None:
    if plan.old_anchor_sha is None or plan.new_anchor_sha is None:
        print("range-diff skipped: stack reaches repository root, so there is no anchor commit.")
        return

    print("\nRange-diff:")
    result = subprocess.run(
        [
            "git",
            "range-diff",
            f"{plan.old_anchor_sha}..{plan.old_tip_sha}",
            f"{plan.new_anchor_sha}..{plan.new_tip_sha}",
        ],
        check=False,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def apply_moves(moves: list[BranchMove]) -> None:
    for move in moves:
        git("branch", "-f", move.branch, move.new_sha)


def push_moves(moves: list[BranchMove], remote: str) -> None:
    branches = [move.branch for move in moves]
    git("push", "--force-with-lease", remote, *branches)


def main() -> int:
    args = parse_args()
    tip = args.tip or current_branch()
    old_tip_rev = args.old_tip or f"{tip}@{{1}}"
    plan = infer_plan(args.base, tip, old_tip_rev, args.match_prefix)

    if args.json:
        print_json(plan)
    else:
        print_plan(plan)

    if args.range_diff:
        show_range_diff(plan)

    if not args.apply and not args.push:
        if not args.json:
            print("\nDry run only. Re-run with --apply to move refs, or add --push to update the remote.")
        return 0

    apply_moves(plan.moves)
    if not args.json:
        print("\nUpdated local refs.")

    if args.push:
        push_moves(plan.moves, args.remote)
        if not args.json:
            print(f"Pushed updated refs to {args.remote}.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
