module

public import Mathlib.Algebra.BigOperators.Fin
public import Mathlib.Data.Fintype.BigOperators
import Mathlib.Tactic.FinCases

/-! # The recurrence for OEIS A250346

A word stores the offsets of the entries from their lower bounds. The entry
at zero-based position i is i + w i. Translating every entry by one gives the
one-based convention in OEIS.
-/

@[expose] public section
namespace ConjectureLab.ShiftedArrays
open Finset

abbrev Word (n : ℕ) := Fin n → Fin 4

def hit (d v : ℕ) : ℕ := if d = v then 1 else 0

def occurrences {n : ℕ} (w : Word n) (v : ℕ) : ℕ :=
  ∑ i : Fin n, hit (i.val + (w i).val) v

/-- Literal count of the arrays in the question, including one empty array. -/
noncomputable def count (n : ℕ) : ℕ := by
  classical
  exact ∑ w : Word n, if ∀ v, occurrences w v ≤ 2 then 1 else 0

structure Window where
  first : ℕ
  second : ℕ
  third : ℕ
  deriving DecidableEq

def feasible (s : Window) : Prop := s.first ≤ 2 ∧ s.second ≤ 2 ∧ s.third ≤ 1

def load (s : Window) : ℕ → ℕ
  | 0 => s.first
  | 1 => s.second
  | 2 => s.third
  | _ + 3 => 0

def shift (s : Window) (d : Fin 4) : Window :=
  ⟨s.second + hit d.val 1, s.third + hit d.val 2, hit d.val 3⟩

private theorem load_shift (s : Window) (d : Fin 4) (v : ℕ) :
    load (shift s d) v = load s (v + 1) + hit d.val (v + 1) := by
  match v with
  | 0 | 1 | 2 => simp [load, shift]
  | k + 3 => simp [load, hit, show d.val ≠ k + 3 + 1 by omega]

private theorem load_le {s : Window} (hs : feasible s) (v : ℕ) : load s v ≤ 2 := by
  match v with
  | 0 => exact hs.1
  | 1 => exact hs.2.1
  | 2 => exact hs.2.2.trans (by decide)
  | _ + 3 => exact Nat.zero_le _

private theorem shift_feasible {s : Window} (hs : feasible s) (d : Fin 4)
    (room : load s d.val < 2) : feasible (shift s d) := by
  rcases hs with ⟨ha, hb, hc⟩
  fin_cases d <;> simp_all [feasible, load, shift, hit] <;> omega

def fits {n : ℕ} (s : Window) (w : Word n) : Prop :=
  ∀ v, load s v + occurrences w v ≤ 2

private theorem occ_zero {n : ℕ} (d : Fin 4) (w : Word n) :
    occurrences (Fin.cons d w) 0 = hit d.val 0 := by
  rw [occurrences, Fin.sum_univ_succ]
  simp [hit, Nat.succ_add]

private theorem occ_succ {n : ℕ} (d : Fin 4) (w : Word n) (v : ℕ) :
    occurrences (Fin.cons d w) (v + 1) = hit d.val (v + 1) + occurrences w v := by
  rw [occurrences, Fin.sum_univ_succ]
  simp [occurrences, hit, Nat.succ_add]

private theorem fits_cons {s : Window} (hs : feasible s) {n : ℕ} (d : Fin 4) (w : Word n) :
    fits s (Fin.cons d w) ↔ load s d.val < 2 ∧ fits (shift s d) w := by
  constructor
  · intro h
    have atHead := h d.val
    have contributes : 1 ≤ occurrences (Fin.cons d w) d.val := by
      rw [occurrences, Fin.sum_univ_succ]
      simp [hit]
    refine ⟨by omega, fun v => ?_⟩
    simpa only [load_shift, occ_succ, Nat.add_assoc] using h (v + 1)
  · rintro ⟨room, tail⟩ v
    cases v with
    | zero =>
      rw [occ_zero]
      by_cases hd : d.val = 0
      · rw [hd] at room
        simp [hit, hd]
        omega
      · simpa [hit, hd] using load_le hs 0
    | succ v =>
      simpa only [load_shift, occ_succ, Nat.add_assoc] using tail v

def step (f : Window → ℕ) (s : Window) : ℕ :=
  ∑ d : Fin 4, if load s d.val < 2 then f (shift s d) else 0

def walks : ℕ → Window → ℕ
  | 0 => fun _ => 1
  | n + 1 => step (walks n)

private theorem count_fitting (n : ℕ) (s : Window) (hs : feasible s) :
    (by classical exact ∑ w : Word n, if fits s w then 1 else 0) = walks n s := by
  classical
  induction n generalizing s with
  | zero =>
    have hfit (w : Word 0) : fits s w := by
      intro v
      simpa [occurrences] using load_le hs v
    simp [hfit, walks]
  | succ n ih =>
    rw [← (Fin.consEquiv (fun _ : Fin (n + 1) => Fin 4)).sum_comp
      (fun w => if fits s w then (1 : ℕ) else 0), Fintype.sum_prod_type]
    change (∑ d : Fin 4, ∑ w : Word n, if fits s (Fin.cons d w) then 1 else 0) = step (walks n) s
    unfold step
    apply sum_congr rfl
    intro d _
    by_cases room : load s d.val < 2
    · simpa [fits_cons hs, room] using ih (shift s d) (shift_feasible hs d room)
    · simp [fits_cons hs, room]

theorem count_eq_walks (n : ℕ) : count n = walks n ⟨0, 0, 0⟩ := by
  classical
  have hz (v : ℕ) : load ⟨0, 0, 0⟩ v = 0 := by
    match v with
    | 0 | 1 | 2 | _ + 3 => rfl
  simpa [count, fits, hz] using count_fitting n ⟨0, 0, 0⟩ (by simp [feasible])

private theorem at_zero (s : Window) (hs : feasible s) :
    walks 6 s + 2 * walks 3 s + 5 * walks 2 s = 4 * walks 5 s + walks 0 s := by
  have certificate : ∀ a b : Fin 3, ∀ c : Fin 2,
      let u : Window := ⟨a.val, b.val, c.val⟩
      walks 6 u + 2 * walks 3 u + 5 * walks 2 u = 4 * walks 5 u + walks 0 u := by
    decide +kernel
  exact certificate ⟨s.first, by have := hs.1; omega⟩
    ⟨s.second, by have := hs.2.1; omega⟩ ⟨s.third, by have := hs.2.2; omega⟩

private theorem walks_recurrence (n : ℕ) (s : Window) (hs : feasible s) :
    walks (n + 6) s + 2 * walks (n + 3) s + 5 * walks (n + 2) s =
      4 * walks (n + 5) s + walks n s := by
  induction n generalizing s with
  | zero => exact at_zero s hs
  | succ n ih =>
    change step (walks (n + 6)) s + 2 * step (walks (n + 3)) s + 5 * step (walks (n + 2)) s =
      4 * step (walks (n + 5)) s + step (walks n) s
    simp only [step, mul_sum, ← sum_add_distrib]
    apply sum_congr rfl
    intro d _
    by_cases room : load s d.val < 2
    · simpa [room] using ih (shift s d) (shift_feasible hs d room)
    · simp [room]

/-- The empirical order-six recurrence on A250346, with all terms in ℕ. -/
theorem recurrence (n : ℕ) :
    count (n + 6) + 2 * count (n + 3) + 5 * count (n + 2) =
      4 * count (n + 5) + count n := by
  simpa only [count_eq_walks] using walks_recurrence n ⟨0, 0, 0⟩ (by simp [feasible])

end ConjectureLab.ShiftedArrays
