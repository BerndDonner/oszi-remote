from __future__ import annotations

import math


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def stddev_sample(xs: list[float]) -> float:
    mu = mean(xs)
    s2 = sum((x - mu) ** 2 for x in xs) / (len(xs) - 1)
    return math.sqrt(s2)


def gaussian_pdf(x: float, mu: float, sigma: float) -> float:
    return (1.0 / (sigma * math.sqrt(2.0 * math.pi))) * math.exp(
        -0.5 * ((x - mu) / sigma) ** 2
    )
