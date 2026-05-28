import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(prog="fennec")
    subparsers = parser.add_subparsers(dest="command")

    propagate = subparsers.add_parser("propagate", help="Run sanitizer trust propagation job")
    propagate.add_argument("--org-id", required=True, help="Organisation ID to process")
    propagate.add_argument("--threshold", type=int, default=3, help="Minimum FP verdict count (default: 3)")
    propagate.add_argument(
        "--db-url",
        default="sqlite:///./fennec_signals.db",
        help="SQLAlchemy database URL (default: local SQLite file)",
    )

    # --- scan subcommand ---
    scan_p = subparsers.add_parser("scan", help="Run a security scan")
    scan_mode = scan_p.add_mutually_exclusive_group()
    scan_mode.add_argument("--diff", action="store_true", help="Incremental scan on changed files (default)")
    scan_mode.add_argument("--full", action="store_true", help="Full-repository scan")
    scan_p.add_argument("--format", default="text", choices=["text", "sarif"], help="Output format")
    scan_p.add_argument("--output", default=None, help="Write output to file instead of stdout")
    scan_p.add_argument("--fail-on", default="blocking", choices=["blocking", "any", "none"],
                        help="Exit code policy (default: blocking)")
    scan_p.add_argument("--repo-path", default=".", help="Repository path to scan")
    scan_p.add_argument("--rules-file", default=None, help="Path to custom_rules.yaml")

    # --- rules subcommand group ---
    rules_parser = subparsers.add_parser("rules", help="Custom rule authoring tools")
    rules_sub = rules_parser.add_subparsers(dest="rules_command")

    suggest_p = rules_sub.add_parser("suggest", help="AI-powered rule candidate suggestion")
    suggest_p.add_argument("--field", required=True, choices=["source", "sink", "sanitizer"])
    suggest_p.add_argument("--vuln-class", required=True, help="e.g. cmdi, sqli, xss")
    suggest_p.add_argument("--rules-file", default="custom_rules.yaml")
    suggest_p.add_argument("--neo4j-uri", default="bolt://localhost:7687")
    suggest_p.add_argument("--neo4j-user", default="neo4j")
    suggest_p.add_argument("--neo4j-password", default="fennecpassword")

    dry_run_p = rules_sub.add_parser("dry-run", help="Estimate FP rate of candidate rules")
    dry_run_p.add_argument("--rule-file", required=True, help="Candidate rules YAML file")
    dry_run_p.add_argument("--repo-path", default=".")

    activate_p = rules_sub.add_parser("activate", help="Activate candidate rules")
    activate_p.add_argument("--rule-file", required=True, help="Candidate rules YAML to merge in")
    activate_p.add_argument("--target", default="custom_rules.yaml")
    activate_p.add_argument("--force", action="store_true", help="Bypass FP threshold check")

    args = parser.parse_args()

    if args.command == "scan":
        _handle_scan(args)

    elif args.command == "propagate":
        from fennec.signal.store import SignalStore
        from fennec.signal.propagation import PropagationJob

        store = SignalStore(args.db_url)
        job = PropagationJob(store)
        job.run(args.org_id, threshold=args.threshold)
        print(f"Propagation complete for org '{args.org_id}'")

    elif args.command == "rules":
        _handle_rules(args)

    else:
        parser.print_help()
        sys.exit(1)


def _handle_scan(args) -> None:
    import json as _json
    from fennec.ci.scanner import FailOn, map_exit_code, run_diff_scan, run_full_scan
    from fennec.output.sarif import SarifRenderer

    if args.full:
        findings = run_full_scan(repo_path=args.repo_path, custom_rules_path=args.rules_file)
    else:
        findings = run_diff_scan(repo_path=args.repo_path, custom_rules_path=args.rules_file)

    if args.format == "sarif":
        sarif_doc = SarifRenderer().render(findings)
        output = _json.dumps(sarif_doc, indent=2)
    else:
        count = len(findings)
        output = f"Fennec scan complete: {count} finding(s)."
        for f in findings:
            output += f"\n  [{f.severity.value}] {f.vuln_class} in {f.taint_path.nodes[0].get('file_path','?') if f.taint_path.nodes else '?'}"

    if args.output:
        with open(args.output, "w") as fh:
            fh.write(output)
    else:
        print(output)

    exit_code = map_exit_code(findings, FailOn(args.fail_on))
    sys.exit(exit_code)


def _handle_rules(args) -> None:
    from pathlib import Path
    from fennec.rules.loader import load_rules, RuleValidationError

    if args.rules_command == "suggest":
        from fennec.graph.client import GraphClient
        from fennec.llm.client import LLMClient
        from fennec.rules.suggest import suggest_candidates, run_approval_loop

        with GraphClient(args.neo4j_uri, args.neo4j_user, args.neo4j_password) as graph:
            llm = LLMClient()
            candidates = suggest_candidates(args.field, args.vuln_class, graph, llm)
        run_approval_loop(candidates, args.field, args.vuln_class, Path(args.rules_file))

    elif args.rules_command == "dry-run":
        from fennec.rules.dry_run import dry_run_scan, print_dry_run_report

        try:
            candidate_rules = load_rules(args.rule_file)
        except RuleValidationError as e:
            print(f"Error loading rule file: {e}", file=sys.stderr)
            sys.exit(1)

        # Dry-run with no pre-computed findings (zero-scan mode)
        result = dry_run_scan(candidate_rules, [], repo_path=args.repo_path)
        print_dry_run_report(result)

    elif args.rules_command == "activate":
        import yaml
        from pathlib import Path

        try:
            candidate_rules = load_rules(args.rule_file)
        except RuleValidationError as e:
            print(f"Error loading rule file: {e}", file=sys.stderr)
            sys.exit(1)

        target = Path(args.target)
        existing: dict = {}
        if target.exists():
            with open(target) as fh:
                existing = yaml.safe_load(fh) or {}

        import yaml as _yaml
        candidate_data = candidate_rules.model_dump(exclude_defaults=False)
        if args.force:
            candidate_data["force_activated"] = True

        for key in ("sources", "sinks", "sanitizers", "rules"):
            if candidate_data.get(key):
                existing.setdefault(key, []).extend(candidate_data[key])

        with open(target, "w") as fh:
            _yaml.dump(existing, fh, default_flow_style=False, sort_keys=False)

        flag = " (force_activated=true)" if args.force else ""
        print(f"Rules activated{flag} → {target}")

    else:
        from argparse import ArgumentParser
        import sys
        print("Usage: fennec rules {suggest,dry-run,activate}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
