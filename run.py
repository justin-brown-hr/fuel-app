"""Launch Fuel Reconcile (GUI or CLI)."""
import sys

if __name__ == "__main__":
    if "--cli" in sys.argv:
        argv = [a for a in sys.argv[1:] if a != "--cli"]
        from src.cli import run_cli

        raise SystemExit(run_cli(argv))

    from src.main import main

    raise SystemExit(main())
