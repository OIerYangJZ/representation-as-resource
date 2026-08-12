# Width-axis External Stress Summary

## Core Questions

1. **Does PyZX recover the bounded semantic form 65/93?** No. PyZX completed all representative runs, but its outputs remained in the tens of thousands of gates rather than the bounded semantic form.
2. **Does TKET recover the bounded semantic form 65/93?** No in this configured pipeline. TKET completed the 4k runs with larger outputs and timed out at 10k.

## Analysis
- In the configured pipelines, PyZX/TKET did not recover the bounded form. This highlights the sensitivity to pipeline configuration and supports the need for explicit semantic aggregation.
- These results strengthen the claim that global diagonal representation is the key boundary between flat and semantic compilers.
- Recommendation: Include in the appendix as additional external baseline evidence.
