module

public import ConjectureLab.ShiftedArrays
public import Mathlib.RingTheory.PowerSeries.Basic
import Mathlib.Tactic.Ring

/-! # The ordinary generating function for OEIS A250346

Adjoining the empty array simplifies the numerator to one. Removing its
constant term recovers Colin Barker's positive-length generating function.
-/

@[expose] public section
namespace ConjectureLab.ShiftedArrays

open PowerSeries

/-- The ordinary generating function including the empty array. -/
noncomputable def arraySeries : PowerSeries ℤ := PowerSeries.mk fun n => (count n : ℤ)

/-- The denominator recorded for A250346. -/
noncomputable def denominator : PowerSeries ℤ :=
  1 - 4 * X + 2 * X ^ 3 + 5 * X ^ 4 - X ^ 6

private theorem coeff_X_mul_at (f : PowerSeries ℤ) (n : ℕ) :
    coeff n (X * f) = if 1 ≤ n then coeff (n - 1) f else 0 := by
  simpa using coeff_X_pow_mul' f 1 n

/-- The reciprocal-denominator identity for the series including its constant term. -/
theorem denominator_mul_arraySeries : denominator * arraySeries = 1 := by
  apply PowerSeries.ext
  intro n
  simp only [denominator, sub_mul, add_mul, one_mul, mul_assoc, map_sub, map_add,
    coeff_ofNat_mul, coeff_X_mul_at, coeff_X_pow_mul', coeff_one, arraySeries, coeff_mk]
  by_cases h : n < 6
  · match n with
    | 0 | 1 | 2 | 3 | 4 | 5 =>
      simp only [count_eq_walks]
      decide +kernel
  · obtain ⟨k, rfl⟩ : ∃ k, n = k + 6 := ⟨n - 6, by omega⟩
    simp only [ite_eq_left (show 1 ≤ k + 6 by omega), ite_eq_left (show 3 ≤ k + 6 by omega),
      ite_eq_left (show 4 ≤ k + 6 by omega), ite_eq_left (show 6 ≤ k + 6 by omega),
      ite_eq_right (show k + 6 ≠ 0 by omega), Nat.add_sub_cancel,
      show k + 6 - 1 = k + 5 by omega, show k + 6 - 3 = k + 3 by omega,
      show k + 6 - 4 = k + 2 by omega]
    have r := recurrence k
    omega

/-- The OEIS generating function, starting at length one, in cross-multiplied form. -/
theorem generatingFunction :
    denominator * (arraySeries - 1) = X * (4 - 2 * X ^ 2 - 5 * X ^ 3 + X ^ 5) := by
  rw [mul_sub, denominator_mul_arraySeries, mul_one, denominator]
  ring

end ConjectureLab.ShiftedArrays
