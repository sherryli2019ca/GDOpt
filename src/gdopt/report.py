"""Markdown rendering of profile reports."""

from __future__ import annotations

from .profile import ProfileReport, candidate_tiers


def _pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def profile_markdown(report: ProfileReport, title: str = "GDOpt profile", top: int | None = None, **candidate_kw) -> str:
    cands = candidate_tiers(report, **candidate_kw)
    lines = [f"# {title}", ""]
    lines += [
        f"- trajectories: {report.n_trajectories_train} train / {report.n_trajectories_test} test; "
        f"test steps: {report.n_steps_test}; action options: {report.n_options}",
        f"- agent cost on test trajectories: ${report.total_cost_test:.2f} "
        f"(LLM ≈ ${report.llm_usd_per_prompt_token * 1e6:.2f}/M prompt tokens; Jev/LLM price ratio {report.jev_to_llm_price_ratio:.3f})",
        f"- steps that are tool calls with all arguments already in context: {_pct(report.closed_tool_step_rate)}",
        f"- upper bound on cost saved if every such step skipped the LLM: {_pct(report.max_saving_share)}",
        "",
        "## Actions on test steps",
        "",
        "| action | steps | share |",
        "| --- | ---: | ---: |",
    ]
    total = sum(report.action_counts_test.values()) or 1
    for a, n in sorted(report.action_counts_test.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {a} | {n} | {_pct(n / total)} |")
    tier_counts = {"code": 0, "jev": 0, "llm": 0}
    step_counts = {"code": 0, "jev": 0, "llm": 0}
    for s in report.situations:
        tier_counts[cands[s.leaf_id]] += 1
        step_counts[cands[s.leaf_id]] += s.n_test
    lines += [
        "",
        "## Candidate tiers (stage 2, before any decision-model call)",
        "",
        "| tier | situations | test steps | share of steps |",
        "| --- | ---: | ---: | ---: |",
    ]
    for t in ("code", "jev", "llm"):
        lines.append(f"| {t} | {tier_counts[t]} | {step_counts[t]} | {_pct(step_counts[t] / (report.n_steps_test or 1))} |")
    lines += [
        "",
        "## Situations (sorted by potential saving)",
        "",
        "| # | rule | n test | majority action | maj. acc | norm. entropy | closed tool | latest-rule acc | cost share | max saving | candidate |",
        "| ---: | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    rows = report.situations if top is None else report.situations[:top]
    for s in rows:
        lines.append(
            f"| {s.leaf_id} | `{s.rule}` | {s.n_test} | {s.majority} | {s.majority_test_acc:.2f} | {s.norm_entropy_test:.2f} | "
            f"{_pct(s.closed_tool_rate)} | {_pct(s.latest_rule_acc)} | {_pct(s.cost_share)} | {_pct(s.max_saving_share)} | {cands[s.leaf_id]} |"
        )
    return "\n".join(lines) + "\n"
