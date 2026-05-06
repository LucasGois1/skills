#!/usr/bin/env python3
"""
Parse PITest mutations.xml and report a worklist for the agent.

Usage:
    python parse_mutations.py <path/to/mutations.xml>
    python parse_mutations.py <path/to/mutations.xml> --json

Output (default, human-readable for the agent):
    - Summary counts by status
    - test_strength + mutation_coverage
    - SURVIVED mutants grouped by class+method (Phase 5b worklist)
    - NO_COVERAGE mutants grouped by class+method (Phase 5a worklist)

Output (--json): machine-readable dict for programmatic consumption.

Targets (per skill SKILL.md):
    test_strength      >= 0.80
    mutation_coverage  >= 0.70
"""
import sys
import json
import argparse
import xml.etree.ElementTree as ET
from collections import defaultdict


def parse(xml_path: str) -> dict:
    tree = ET.parse(xml_path)
    root = tree.getroot()

    counts = defaultdict(int)
    survived = []
    no_coverage = []

    for m in root.findall("mutation"):
        status = m.get("status", "UNKNOWN")
        counts[status] += 1
        if status not in ("SURVIVED", "NO_COVERAGE"):
            continue
        record = {
            "status": status,
            "class": m.findtext("mutatedClass", ""),
            "method": m.findtext("mutatedMethod", ""),
            "line": int(m.findtext("lineNumber", "0") or 0),
            "mutator": (m.findtext("mutator", "") or "").split(".")[-1],
            "description": m.findtext("description", ""),
            "source_file": m.findtext("sourceFile", ""),
        }
        if status == "SURVIVED":
            survived.append(record)
        else:
            no_coverage.append(record)

    killed = counts.get("KILLED", 0)
    surv = counts.get("SURVIVED", 0)
    no_cov = counts.get("NO_COVERAGE", 0)
    timed_out = counts.get("TIMED_OUT", 0)

    covered = killed + surv
    total = killed + surv + no_cov + timed_out

    test_strength = (killed / covered) if covered else 0.0
    mutation_coverage = (killed / total) if total else 0.0

    return {
        "counts": dict(counts),
        "test_strength": round(test_strength, 4),
        "mutation_coverage": round(mutation_coverage, 4),
        "test_strength_target_met": test_strength >= 0.80,
        "mutation_coverage_target_met": mutation_coverage >= 0.70,
        "survived": survived,
        "no_coverage": no_coverage,
    }


def group_by_method(records):
    grouped = defaultdict(list)
    for r in records:
        key = f"{r['class']}#{r['method']}"
        grouped[key].append(r)
    return grouped


def render_text(report: dict) -> str:
    lines = []
    lines.append("=" * 70)
    lines.append("PITest Mutation Report")
    lines.append("=" * 70)
    lines.append("")
    lines.append("Counts by status:")
    for status, n in sorted(report["counts"].items()):
        lines.append(f"  {status:<14} {n}")
    lines.append("")

    ts = report["test_strength"]
    mc = report["mutation_coverage"]
    ts_flag = "OK" if report["test_strength_target_met"] else "BELOW TARGET (0.80)"
    mc_flag = "OK" if report["mutation_coverage_target_met"] else "BELOW TARGET (0.70)"
    lines.append(f"Test Strength      : {ts:.2%}  [{ts_flag}]")
    lines.append(f"Mutation Coverage  : {mc:.2%}  [{mc_flag}]")
    lines.append("")

    if report["no_coverage"]:
        lines.append("-" * 70)
        lines.append(f"NO_COVERAGE worklist (Phase 5a — write tests that exercise the code)")
        lines.append(f"  {len(report['no_coverage'])} mutants in uncovered code")
        lines.append("-" * 70)
        for method, mutants in sorted(group_by_method(report["no_coverage"]).items()):
            class_method = method.replace("#", " :: ")
            mutators = sorted({m["mutator"] for m in mutants})
            line_nums = sorted({m["line"] for m in mutants})
            lines.append(f"  {class_method}")
            lines.append(f"    lines:    {line_nums}")
            lines.append(f"    mutants:  {len(mutants)}")
            lines.append(f"    mutators: {mutators}")
        lines.append("")

    if report["survived"]:
        lines.append("-" * 70)
        lines.append(f"SURVIVED worklist (Phase 5b — strengthen assertions)")
        lines.append(f"  {len(report['survived'])} mutants escaped the suite")
        lines.append("-" * 70)
        for r in sorted(report["survived"], key=lambda x: (x["class"], x["line"])):
            lines.append(f"  L{r['line']:<5} {r['class']}#{r['method']}")
            lines.append(f"        mutator: {r['mutator']}")
            lines.append(f"        change:  {r['description']}")
        lines.append("")

    if not report["survived"] and not report["no_coverage"]:
        lines.append("All mutants killed. Done.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("xml_path", help="Path to PITest mutations.xml")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of text report")
    args = parser.parse_args()

    try:
        report = parse(args.xml_path)
    except FileNotFoundError:
        print(f"ERROR: file not found: {args.xml_path}", file=sys.stderr)
        sys.exit(2)
    except ET.ParseError as e:
        print(f"ERROR: invalid XML: {e}", file=sys.stderr)
        sys.exit(2)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render_text(report))

    # Exit 0 if both targets met, 1 if work remains. Useful for CI gates.
    sys.exit(0 if report["test_strength_target_met"] and report["mutation_coverage_target_met"] else 1)


if __name__ == "__main__":
    main()
