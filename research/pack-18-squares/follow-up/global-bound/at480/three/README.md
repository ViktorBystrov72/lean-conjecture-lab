# Three split orbits at side 4.80

Orbits 22, 54 and 132 each have two complementary leaves in the pinned base cut table. The independent solver excluded all six with the container walls set directly to side $24/5$. The unchanged rack box has side $4.822876$; the true wall inset on each side is $(4.822876-4.80)/2=0.011438$. These results can therefore be combined directly with the other orbit families at side $24/5$.

| Orbit | Mask | Leaf 0 | Leaf 1 |
| ---: | --- | --- | --- |
| 22 | 1bfbfb | Owner 14 empty, round 9 | Owner 9 empty, round 10 |
| 54 | 1efbfb | Owner 9 empty, round 9 | Owner 0 empty, round 7 |
| 132 | 1ffafe | Owner 16 empty, round 11 | Owner 13 empty, round 12 |

The replay checks the input digest, independently enumerates the orbit correspondence, and verifies that the paths cover both sides of every split. It takes the angular bands and round budgets from the earlier larger-box run, then recomputes every contradiction in the smaller box. The larger-box result also implies the exclusion by inclusion of concentric containers. [Geometry and coverage](../../../empty-cover/README.md) · [Numerical receipt](receipt.json)

With a C++17 compiler and Python 3, run from this directory:

```sh
python3 verify.py --jobs 2
```

The default fetches the pinned data table. Use `--source /path/to/git/clone` or `--table /path/to/n18-482-base.json` to avoid network access. To reuse an independent angle checker built with `empty-cover/build.py --endpoint-supports`, pass `--exe /path/to/program`.
