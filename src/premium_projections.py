from __future__ import annotations

from io import BytesIO
from typing import List

import matplotlib.pyplot as plt

from .policy_schema import PremiumProjectionGroup


def generate_premium_chart(projections: List[PremiumProjectionGroup]) -> bytes:
    """Generate a PNG chart showing premium growth over time."""
    fig, ax = plt.subplots(figsize=(7, 4))

    if not projections:
        ax.text(0.5, 0.5, "No premium projections", ha="center", va="center")
        ax.axis("off")
    else:
        for group in projections:
            label = group.coverage or group.appendix or "Projection"
            ages = [p.age for p in group.projections if p.age is not None and p.monthly is not None]
            premiums = [p.monthly for p in group.projections if p.age is not None and p.monthly is not None]
            if ages and premiums:
                ax.plot(ages, premiums, marker="o", label=label)

        ax.set_xlabel("Age")
        ax.set_ylabel("Monthly Premium")
        ax.set_title("Premium Projections")
        ax.grid(True, alpha=0.3)
        if ax.get_legend_handles_labels()[0]:
            ax.legend(loc="best")

    output = BytesIO()
    fig.tight_layout()
    fig.savefig(output, format="png", dpi=150)
    plt.close(fig)
    output.seek(0)
    return output.read()
