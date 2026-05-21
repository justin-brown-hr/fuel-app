"""Launch Fuel Reconcile (GUI or CLI)."""
import sys

if __name__ == "__main__":
    if "--cli" not in sys.argv:
        from src.frozen_check import ensure_frozen_layout

        if not ensure_frozen_layout():
            raise SystemExit(1)

    if "--cli" in sys.argv:
        argv = [a for a in sys.argv[1:] if a != "--cli"]
        from src.cli import run_cli

        raise SystemExit(run_cli(argv))

    from src.main import main

    raise SystemExit(main())
