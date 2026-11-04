"""
Fractional Indexing & Deterministic Column Rebalance Service

Implements rank allocation between Kanban cards:
- Base spacing: 1000.0
- Midpoint allocation: (R_prev + R_next) / 2.0
- Rank exhaustion threshold: epsilon = 1e-6
- Deterministic column rebalancing with (rank ASC, id ASC) ordering.
"""

from typing import List, Tuple
import uuid

BASE_SPACING = 1000.0
MIN_GAP_EPSILON = 1e-6


class FractionalIndexService:
    @classmethod
    def calculate_rank(
        cls,
        prev_rank: float | None,
        next_rank: float | None,
    ) -> Tuple[float, bool]:
        """
        Calculates the new fractional rank given previous and next neighboring ranks.
        Returns (new_rank, needs_rebalance).
        """
        # Case 1: Empty column or neither neighbor present
        if prev_rank is None and next_rank is None:
            return BASE_SPACING, False

        # Case 2: Inserted at beginning (before next_rank)
        if prev_rank is None and next_rank is not None:
            if next_rank <= MIN_GAP_EPSILON:
                # Rank underflow at the very beginning -> rebalance required
                return BASE_SPACING / 2.0, True
            return next_rank / 2.0, False

        # Case 3: Inserted at end (after prev_rank)
        if prev_rank is not None and next_rank is None:
            return prev_rank + BASE_SPACING, False

        # Case 4: Inserted between prev_rank and next_rank
        assert prev_rank is not None and next_rank is not None

        # Sanity check if ranks are inverted
        if prev_rank >= next_rank:
            return (prev_rank + next_rank) / 2.0, True

        gap = next_rank - prev_rank
        if gap < MIN_GAP_EPSILON:
            # Rank exhaustion detected -> trigger rebalance
            return (prev_rank + next_rank) / 2.0, True

        return (prev_rank + next_rank) / 2.0, False

    @classmethod
    def rebalance_ranks(
        cls,
        items: List[Tuple[uuid.UUID, float]],
    ) -> List[Tuple[uuid.UUID, float]]:
        """
        Deterministically rebalances an ordered list of (id, current_rank) tuples.
        Reassigns ranks starting from 1000.0 in increments of 1000.0.
        """
        rebalanced = []
        current = BASE_SPACING
        for item_id, _ in items:
            rebalanced.append((item_id, current))
            current += BASE_SPACING
        return rebalanced


fractional_index_service = FractionalIndexService()

