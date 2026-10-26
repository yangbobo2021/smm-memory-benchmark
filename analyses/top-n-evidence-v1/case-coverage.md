# Per-case registered evidence coverage

Minimum cutoff within 1–5; `>5` means incomplete in the tested cutoffs. Each union cutoff takes that many from **both** routes, then deduplicates.

| Case | Atoms | Official refs | BM25 necessary / official | Vector necessary / official | Union necessary / official |
|---|---:|---:|---|---|---|
| [P01](../../docs/cases/P01.md) | 1 | 2 | 1 / 2 | 1 / 2 | 1 / 2 |
| [P02](../../docs/cases/P02.md) | 1 | 2 | 2 / 2 | 1 / 2 | 1 / 1 |
| [P03](../../docs/cases/P03.md) | 1 | 2 | 2 / 2 | 2 / 2 | 2 / 2 |
| [P04](../../docs/cases/P04.md) | 1 | 2 | 1 / 2 | 2 / 2 | 1 / 1 |
| [P05](../../docs/cases/P05.md) | 1 | 2 | 1 / 2 | 1 / 2 | 1 / 2 |
| [P06](../../docs/cases/P06.md) | 2 | 2 | 3 / 3 | 4 / 4 | 3 / 3 |
| [P07](../../docs/cases/P07.md) | 3 | 2 | 3 / 3 | 3 / 3 | 1 / 1 |
| [P08](../../docs/cases/P08.md) | 2 | 4 | 4 / 4 | 4 / 4 | 4 / 4 |
| [P09](../../docs/cases/P09.md) | 3 | 3 | 4 / 4 | 3 / 3 | 2 / 2 |
| [P10](../../docs/cases/P10.md) | 2 | 3 | 1 / 4 | 2 / >5 | 1 / 4 |
| [P11](../../docs/cases/P11.md) | 1 | 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| [P12](../../docs/cases/P12.md) | 1 | 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| [P13](../../docs/cases/P13.md) | 1 | 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| [P14](../../docs/cases/P14.md) | 1 | 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| [P15](../../docs/cases/P15.md) | 1 | 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| [P16](../../docs/cases/P16.md) | 1 | 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| [P17](../../docs/cases/P17.md) | 1 | 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| [P18](../../docs/cases/P18.md) | 1 | 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| [P19](../../docs/cases/P19.md) | 1 | 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| [P20](../../docs/cases/P20.md) | 1 | 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| [P21](../../docs/cases/P21.md) | 3 | 3 | 3 / 3 | 4 / 4 | 3 / 3 |
| [P22](../../docs/cases/P22.md) | 1 | 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| [P23](../../docs/cases/P23.md) | 2 | 2 | 2 / 2 | 2 / 2 | 2 / 2 |
| [P24](../../docs/cases/P24.md) | 1 | 1 | 1 / 1 | >5 / >5 | 1 / 1 |
| [P25](../../docs/cases/P25.md) | 2 | 2 | 2 / 2 | 2 / 2 | 1 / 1 |

## Missing necessary evidence by cutoff

- bm25 Top1: P02, P03, P06, P07, P08, P09, P21, P23, P25
- bm25 Top2: P06, P07, P08, P09, P21
- bm25 Top3: P08, P09
- bm25 Top4: none
- bm25 Top5: none
- vector Top1: P03, P04, P06, P07, P08, P09, P10, P21, P23, P24, P25
- vector Top2: P06, P07, P08, P09, P21, P24
- vector Top3: P06, P08, P21, P24
- vector Top4: P24
- vector Top5: P24
- union Top1: P03, P06, P08, P09, P21, P23
- union Top2: P06, P08, P21
- union Top3: P08
- union Top4: none
- union Top5: none
