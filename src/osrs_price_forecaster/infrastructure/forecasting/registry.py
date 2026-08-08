from collections.abc import Sequence
from dataclasses import dataclass

from osrs_price_forecaster.domain.forecasting import CandidateModelRegistry, ForecastModel


@dataclass(slots=True)
class InMemoryCandidateModelRegistry(CandidateModelRegistry):
    """Simple registry placeholder for candidate forecast models.

    Phase 1 will register baseline candidates (naive, rolling mean, EWMA,
    linear trend) and metadata required for evaluation.
    """

    _models: Sequence[ForecastModel]

    def list_candidates(self) -> Sequence[ForecastModel]:
        return self._models
