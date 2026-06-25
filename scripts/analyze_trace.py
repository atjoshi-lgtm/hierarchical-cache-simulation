"""Analysis script for CDN simulator trace logs with popularity distribution visualization."""

from collections import Counter
import numpy as np
import matplotlib.pyplot as plt
from src.simulator.data_access.parser import parse_trace_file


TRACE_FILE = "data/request_seq_small"


def main():
    """Parse trace file, calculate core metrics, and plot popularity distribution."""
    
    # Initialize tracking variables
    total_requests = 0
    total_bytes_requested = 0
    min_ts = float('inf')
    max_ts = 0
    unique_objects = {}  # Maps cachekey -> latest file_size
    sizes_list = []
    request_counts = Counter()
    
    # Parse trace file using generator (O(1) memory)
    print("Parsing trace file...")
    for trace in parse_trace_file(TRACE_FILE):
        total_requests += 1
        total_bytes_requested += trace.file_size
        
        # Update timestamps
        min_ts = min(min_ts, trace.timestamp)
        max_ts = max(max_ts, trace.timestamp)
        
        # Track unique objects and their latest file size
        if trace.cachekey not in unique_objects:
            sizes_list.append(trace.file_size)
        unique_objects[trace.cachekey] = trace.file_size
        
        # Count requests per cachekey
        request_counts[trace.cachekey] += 1
    
    # Calculate post-loop metrics
    wall_clock_seconds = max_ts - min_ts
    working_set_bytes = sum(unique_objects.values())
    
    # Object size statistics
    min_size = min(sizes_list)
    max_size = max(sizes_list)
    avg_size = np.mean(sizes_list)
    
    # Print formatted summary
    print("\n" + "=" * 60)
    print("CDN SIMULATOR TRACE ANALYSIS SUMMARY")
    print("=" * 60)
    print(f"Total Requests:              {total_requests:,}")
    print(f"Total Bytes Requested:       {total_bytes_requested:,} bytes")
    print(f"Unique Objects:              {len(unique_objects):,}")
    print(f"Wall-Clock Timespan:         {wall_clock_seconds:,} seconds")
    print(f"Working Set Size (Total):    {working_set_bytes:,} bytes")
    print(f"Minimum Object Size:         {min_size:,} bytes")
    print(f"Maximum Object Size:         {max_size:,} bytes")
    print(f"Average Object Size:         {avg_size:,.2f} bytes")
    print("=" * 60 + "\n")
    
    # Create popularity distribution plot
    print("Creating popularity distribution plot...")
    
    # Extract and sort frequencies
    frequencies = sorted(request_counts.values(), reverse=True)
    ranks = np.arange(1, len(frequencies) + 1)
    
    # Create log-log plot
    plt.figure(figsize=(10, 6))
    plt.loglog(ranks, frequencies, marker='o', markersize=3, linestyle='none', alpha=0.6)
    plt.xlabel("Object Rank", fontsize=12)
    plt.ylabel("Request Frequency", fontsize=12)
    plt.title("Complete Popularity Distribution", fontsize=14, fontweight='bold')
    plt.grid(True, which="both", alpha=0.3)
    plt.tight_layout()
    
    # Save plot
    plt.savefig("popularity_distribution.png", dpi=150, bbox_inches='tight')
    print("Plot saved to popularity_distribution.png\n")


if __name__ == "__main__":
    main()
