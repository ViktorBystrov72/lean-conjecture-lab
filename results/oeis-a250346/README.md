# A proof of the recurrence for OEIS A250346

R. H. Hardin asked how many arrays of length $n$ satisfy two restrictions. At position $i$, the entry belongs to $\{i,i+1,i+2,i+3\}$, and each integer occurs at most twice in the whole array. Write $a_n$ for their number and set $a_0=1$ for the empty array. For length three there are $4^3$ candidates. Only $(3,3,3)$ and $(4,4,4)$ violate the multiplicity restriction, giving $a_3=62$.

## Theorem

For every $n\ge 0$,

$$
a_{n+6}+2a_{n+3}+5a_{n+2}=4a_{n+5}+a_n .
$$

Together with $(a_0,\ldots,a_5)=(1,4,16,62,235,888)$ this determines the sequence for every length. Its ordinary generating function with the OEIS offset is

$$
\sum_{n\ge1}a_n x^n
=\frac{x(4-2x^2-5x^3+x^5)}{1-4x+2x^3+5x^4-x^6}.
$$

Hardin recorded the recurrence as empirical on November 19, 2014 (revision 3). Colin Barker recorded the generating function on November 12, 2018 (revision 6). [Original entry](https://oeis.org/A250346) · [Revision history](https://oeis.org/history?seq=A250346)

## Proof

Just before filling position $i$, record the prior multiplicities $(u,v,w)$ of $i,i+1,i+2$. Smaller values can never occur again. The value $i+3$ has never occurred, and only the immediately preceding position could have used $i+2$. Thus $u,v\in\{0,1,2\}$ and $w\in\{0,1\}$, giving 18 states to check.

| Entry chosen | Condition | State at position $i+1$ |
| --- | --- | --- |
| $i$ | $u<2$ | $(v,w,0)$ |
| $i+1$ | $v<2$ | $(v+1,w,0)$ |
| $i+2$ | Always | $(v,w+1,0)$ |
| $i+3$ | Always | $(v,w,1)$ |

Let $b_k(s)$ count the ways to fill $k$ more positions from state $s$. Then $b_0(s)=1$. Each valid array determines exactly one sequence of choices, so $b_{k+1}(s)$ is the sum of $b_k$ over the permitted transitions in the table and $a_k=b_k(0,0,0)$.

Applying those transitions six times gives the following certificate. States on the same line give identical displayed counts. For example, the first line gives $3349+2\cdot62+5\cdot16=4\cdot888+1$.

| States $uvw$ | $b_2$ | $b_3$ | $b_5$ | $b_6$ |
| --- | ---: | ---: | ---: | ---: |
| 000, 100 | 16 | 62 | 888 | 3349 |
| 001, 101 | 15 | 53 | 747 | 2808 |
| 010, 110 | 15 | 58 | 826 | 3114 |
| 011, 111 | 14 | 49 | 685 | 2573 |
| 020, 120 | 9 | 34 | 471 | 1772 |
| 021, 121 | 8 | 27 | 362 | 1355 |
| 200 | 12 | 46 | 653 | 2461 |
| 201 | 11 | 38 | 528 | 1982 |
| 210 | 11 | 42 | 591 | 2226 |
| 211 | 10 | 34 | 466 | 1747 |
| 220 | 6 | 22 | 298 | 1119 |
| 221 | 5 | 16 | 205 | 764 |

Every row satisfies $b_6+2b_3+5b_2=4b_5+b_0$. Suppose the same identity holds with every index increased by $n$ at every state. Fix a state $s$ and sum the identities for its permitted next states. By the transition rule each sum is the corresponding count at $s$ with its index increased by one. This proves the identity for every $n$ by induction. The empty starting state gives Hardin’s recurrence.

To recover Barker’s formula, put $B(x)=\sum_{n\ge0}a_n x^n$ and $D(x)=1-4x+2x^3+5x^4-x^6$. The recurrence makes every coefficient of $D(x)B(x)$ in degree at least six zero. The initial counts give coefficients $1,0,0,0,0,0$ in degrees zero through five. Hence $D(x)B(x)=1$, and subtracting the empty array gives the displayed generating function.

## A second derivation by forbidden words

Write down the offsets from the lower bounds as a word on the digits 0 through 3. Three equal entries must occur within four consecutive positions, since the value at position $i$ is at most $i+3$. In three consecutive positions the offsets giving equal entries are 210 and 321. If the first and last positions of a four-letter word have equal entries, its first digit must be 3 and its last digit 0. To match them, the second digit must be 2 or the third digit 1. Removing words that already contain a forbidden triple leaves six minimal forbidden words of length four.

| Length | Minimal forbidden words |
| --- | --- |
| 3 | 210, 321 |
| 4 | 3010, 3110, 3200, 3220, 3230, 3310 |

Mark an arbitrary subset of the forbidden occurrences in each word. Give a word with $k$ marks weight $(-1)^k$. Summing over its markings gives one for an admissible word and zero for any word containing a forbidden occurrence. A marked word breaks uniquely into individual uncovered letters and connected groups of overlapping marked occurrences.

The only proper suffix–prefix overlaps in the table are 321 with 210, giving 3210, and 3230 with 3010, giving 323010. Neither group can extend to a third overlapping mark. Hence the signed contributions of the pieces are $4x$ for free letters, $-2x^3-6x^4$ for single marks and $x^4+x^6$ for double marks. Summing all sequences of pieces gives $1/(1-4x+2x^3+5x^4-x^6)$, including the empty word. This applies classical inclusion–exclusion for forbidden subwords to the array restrictions. [Guibas and Odlyzko on string overlaps](https://doi.org/10.1016/0097-3165(81)90005-4)

## Verification and prior work

The Lean proof starts with the count of all offset words satisfying the multiplicity bound. It proves the link to the transition system, the recurrence for all lengths, and the identity of formal power series over the integers. The Python verifier also enumerates short arrays directly. [Lean recurrence](../../ConjectureLab/ShiftedArrays.lean) · [Lean generating function](../../ConjectureLab/ShiftedArraysSeries.lean) · [Axiom audit](Audit.lean) · [Python verifier](verify.py) · [Replay commands](../../README.md#verify)

As of November 27, 2026, the OEIS entry and its parent table label the recurrence empirical. A search by sequence number, initial terms, formula and array restrictions found no earlier proof of this specific formula. The finite-state argument was developed for this repository with AI assistance. Publication priority remains unestablished. [Parent table A250351](https://oeis.org/A250351)
