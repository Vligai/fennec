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

    args = parser.parse_args()

    if args.command == "propagate":
        from fennec.signal.store import SignalStore
        from fennec.signal.propagation import PropagationJob

        store = SignalStore(args.db_url)
        job = PropagationJob(store)
        job.run(args.org_id, threshold=args.threshold)
        print(f"Propagation complete for org '{args.org_id}'")
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
