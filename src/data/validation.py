"""Small validation helpers shared by the data pipeline."""
from typing import Iterable


def missing_years(expected_years: Iterable[int], observed_years: Iterable[int]) -> list[int]:
    """Return expected years not found among observed years, in sorted order."""
    observed = set(observed_years)
    return sorted(year for year in set(expected_years) if year not in observed)
