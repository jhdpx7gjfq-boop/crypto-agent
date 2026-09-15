"""Small, explicit statistics used by the validation layer.

Hand-rolled on the standard library on purpose: every number in a validation
report should be traceable to a few lines of readable arithmetic.
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def ranks(values: Sequence[float]) -> list[float]:
    """Ranks, 1-based, with ties sharing their average rank."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    result = [0.0] * len(values)
    position = 0
    while position < len(order):
        end = position
        while end + 1 < len(order) and values[order[end + 1]] == values[order[position]]:
            end += 1
        average = (position + end) / 2 + 1
        for index in order[position : end + 1]:
            result[index] = average
        position = end + 1
    return result


def spearman(x: Sequence[float], y: Sequence[float]) -> float | None:
    """Spearman rank correlation. ``None`` when undefined (n < 3 or no spread)."""
    if len(x) != len(y):
        raise ValueError("x and y must have the same length")
    if len(x) < 3:
        return None
    return pearson(ranks(x), ranks(y))


def pearson(x: Sequence[float], y: Sequence[float]) -> float | None:
    n = len(x)
    if n < 2:
        return None
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    covariance = sum((a - mean_x) * (b - mean_y) for a, b in zip(x, y))
    variance_x = sum((a - mean_x) ** 2 for a in x)
    variance_y = sum((b - mean_y) ** 2 for b in y)
    if variance_x == 0 or variance_y == 0:
        return None
    return covariance / math.sqrt(variance_x * variance_y)


def mean(values: Sequence[float]) -> float | None:
    return sum(values) / len(values) if values else None


def stdev(values: Sequence[float]) -> float | None:
    """Sample standard deviation (n-1)."""
    n = len(values)
    if n < 2:
        return None
    average = sum(values) / n
    return math.sqrt(sum((value - average) ** 2 for value in values) / (n - 1))


def t_statistic(values: Sequence[float]) -> float | None:
    """t-stat of the sample mean against zero.

    Independence is assumed and, for overlapping forward returns, not strictly
    true — read it as an order of magnitude, not a p-value.
    """
    n = len(values)
    if n < 2:
        return None
    deviation = stdev(values)
    if not deviation:
        return None
    return (sum(values) / n) / (deviation / math.sqrt(n))


def median(values: Sequence[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2
