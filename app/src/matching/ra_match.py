from src.importers.utils import normalize_ra


def ra_matches(branch_ra: str, other_ra: str) -> bool:
    if not branch_ra or not other_ra:
        return True
    if branch_ra == other_ra:
        return True
    shorter, longer = (
        (branch_ra, other_ra) if len(branch_ra) <= len(other_ra) else (other_ra, branch_ra)
    )
    if len(shorter) >= 6 and longer.startswith(shorter):
        return True
    return False


def match_key(ra: str, tx_date) -> tuple[str, str]:
    return (normalize_ra(ra), tx_date.isoformat())
