# Recovered parity fixtures

These fixtures are small, reviewable facts extracted from the Norwegian 1.6 SWF.
They are intended to become executable parity tests as the Decay test harness
matures.

| SWF frame | Preconditions | Random inputs | Writes / decision | Destination | Confidence |
| ---: | --- | --- | --- | --- | --- |
| 202 | new game | original `RandomNumber` stream | `level=1`, `goto_label=bane1_start`, `topTime=0`, `cool=0`, `speed=20`, `energi=1`, `penge=5000` | first route | confirmed |
| 368 | `goto_label=level1` | none | route by label | SWF frame index 482 | confirmed |
| 368 | `goto_label=level2` | none | route by label | SWF frame index 491 | confirmed |
| 368 | `goto_label=level3` | none | route by label | SWF frame index 501 | confirmed |
| 529 | `cool < 200` | none | status tier 1 | status frame group 1 | confirmed |
| 529 | `199 < cool < 600` | none | status tier 2 | status frame group 2 | confirmed |
| 529 | `599 < cool < 1200` | none | status tier 3 | status frame group 3 | confirmed |
| 529 | `1199 < cool < 2500` | none | status tier 4 | status frame group 4 | confirmed |
| 529 | `cool > 2499` | none | status tier 5 | status frame group 5 | confirmed |
| 743 | any current `cool` | none | `cool_old=cool` | route dispatcher | confirmed |
| 794 | entering gameplay | seven original `RandomNumber` draws | reset run flags and place `fetter_1..4`, `pige_1..3` | gameplay | confirmed |
| 809 | `goto_label=level1` | none | level dispatch | SWF frame index 482 | confirmed |
| 809 | `goto_label=level2` | none | level dispatch | SWF frame index 491 | confirmed |
| 809 | `goto_label=level3` | none | level dispatch | SWF frame index 501 | confirmed |

SWF `GotoFrame` indices are zero-based. Main-timeline frame numbers used by the
analysis reports are one-based, so those two numbers must not be compared as if
they used the same convention. Twenty-three-year-old Flash archaeology already
has enough traps without donating another one.
