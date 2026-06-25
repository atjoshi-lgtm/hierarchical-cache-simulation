"""Experiment: sweep edge disk size with parent fixed; plot 4 core metrics."""

import matplotlib.pyplot as plt

from src.simulator.engine.orchestrator import SimulationEngine
from src.simulator.models.lru_cache import ByteAwareLRUCache


TRACE_FILE = "data/request_seq_small"

GB = 1_000_000_000
PARENT_BYTES = 120 * GB
EDGE_SIZES_GB = [6, 12, 24, 48, 96, 120]


def run_single(edge_bytes: int) -> dict[str, float]:
    edge_cache = ByteAwareLRUCache(edge_bytes)
    parent_cache = ByteAwareLRUCache(PARENT_BYTES)
    engine = SimulationEngine(edge_cache, parent_cache, TRACE_FILE)
    return engine.run()


def main() -> None:
    edge_hit_rates = []
    parent_conditional_hit_rates = []
    global_hit_rates = []
    duplication_byte_rates = []

    for size_gb in EDGE_SIZES_GB:
        print(f"Running edge={size_gb} GB, parent={PARENT_BYTES // GB} GB ...")
        m = run_single(size_gb * GB)

        R = m["total_requests"]
        He = m["edge_hits"]
        Hp = m["parent_hits"]
        Me = R - He  # edge misses = parent's request load

        edge_hit_rates.append(He / R)
        parent_conditional_hit_rates.append(Hp / Me if Me > 0 else 0.0)
        global_hit_rates.append((He + Hp) / R)
        duplication_byte_rates.append(m["duplication_byte_rate"])

        print(
            f"  edge_hr={edge_hit_rates[-1]:.4f}  "
            f"parent_cond_hr={parent_conditional_hit_rates[-1]:.4f}  "
            f"global_hr={global_hit_rates[-1]:.4f}  "
            f"dup_byte_rate={duplication_byte_rates[-1]:.4f}"
        )

    # Plot
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle(
        f"Hierarchical Cache Experiment\n"
        f"(Parent fixed at {PARENT_BYTES // GB} GB, Edge swept)",
        fontsize=13,
        fontweight="bold",
    )

    x = EDGE_SIZES_GB
    plots = [
        (axes[0, 0], edge_hit_rates,                "Edge Hit Rate",                    "Hit Rate"),
        (axes[0, 1], parent_conditional_hit_rates,  "Parent Conditional Hit Rate",      "Hit Rate"),
        (axes[1, 0], global_hit_rates,              "Global Hit Rate",                  "Hit Rate"),
        (axes[1, 1], duplication_byte_rates,        "Duplication Byte Rate\n(parent bytes also in edge)", "Rate"),
    ]

    for ax, values, title, ylabel in plots:
        ax.plot(x, values, marker="o", linewidth=2, markersize=6)
        ax.set_xscale("log")
        ax.set_xlabel("Edge Disk Size (GB)", fontsize=10)
        ax.set_ylabel(ylabel, fontsize=10)
        ax.set_title(title, fontsize=11)
        ax.set_xticks(x)
        ax.set_xticklabels([str(s) for s in x])
        ax.set_ylim(0, 1)
        ax.grid(True, which="both", alpha=0.3)

    plt.tight_layout()
    plt.savefig("experiment_results.png", dpi=150, bbox_inches="tight")
    print("\nPlot saved to experiment_results.png")


if __name__ == "__main__":
    main()
