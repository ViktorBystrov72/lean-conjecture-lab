module

public import Init

/-! # The classical Collatz conjecture

The open statement is a proposition. The theorems below prove that the single-division
shortcut gives the same reachability question and check the example starting at 27.
-/

@[expose] public section
namespace ConjectureLab.Collatz

/-- One ordinary step, including the even value immediately after an odd step. -/
def step (n : Nat) : Nat :=
  if n % 2 = 0 then n / 2 else 3 * n + 1

/-- Combine an odd step with the one division by two that necessarily follows. -/
def shortcut (n : Nat) : Nat :=
  if n % 2 = 0 then n / 2 else (3 * n + 1) / 2

/-- The value after exactly `k` applications of `f`, counting the starting value as step zero. -/
def orbit (f : Nat → Nat) : Nat → Nat → Nat
  | 0, n => n
  | k + 1, n => orbit f k (f n)

def ReachesOne (f : Nat → Nat) (n : Nat) : Prop := ∃ k, orbit f k n = 1

/-- The open conjecture quantifies over all positive starting values. -/
def CollatzConjecture : Prop := ∀ n : Nat, 0 < n → ReachesOne step n

private theorem ordinary_of_shortcut (k n : Nat) (h : orbit shortcut k n = 1) :
    ReachesOne step n := by
  induction k generalizing n with
  | zero => exact ⟨0, h⟩
  | succ k ih =>
    obtain ⟨j, hj⟩ := ih (shortcut n) h
    by_cases he : n % 2 = 0
    · exact ⟨j + 1, by simpa [orbit, shortcut, step, he] using hj⟩
    · have he' : (3 * n + 1) % 2 = 0 := by omega
      exact ⟨j + 2, by simpa [orbit, shortcut, step, he, he'] using hj⟩

private theorem shortcut_of_ordinary (k n : Nat) (h : orbit step k n = 1) :
    ReachesOne shortcut n := by
  induction k generalizing n with
  | zero => exact ⟨0, h⟩
  | succ k ih =>
    obtain ⟨j, hj⟩ := ih (step n) h
    by_cases he : n % 2 = 0
    · exact ⟨j + 1, by simpa [orbit, shortcut, step, he] using hj⟩
    · have he' : (3 * n + 1) % 2 = 0 := by omega
      cases j with
      | zero =>
        simp [orbit, step, he] at hj
        omega
      | succ j =>
        exact ⟨j + 1, by simpa [orbit, shortcut, step, he, he'] using hj⟩

/-- Both maps reach 1 from exactly the same starting values. -/
theorem reachesOne_iff_shortcut (n : Nat) : ReachesOne step n ↔ ReachesOne shortcut n := by
  constructor
  · rintro ⟨k, hk⟩
    exact shortcut_of_ordinary k n hk
  · rintro ⟨k, hk⟩
    exact ordinary_of_shortcut k n hk

set_option maxRecDepth 4096 in
/-- 27 first reaches 1 at step 111. Its peak on this segment is 9232, reached at step 77. -/
theorem orbit_27 :
    orbit step 111 27 = 1 ∧
    (∀ k : Fin 111, orbit step k.val 27 ≠ 1) ∧
    orbit step 77 27 = 9232 ∧
    (∀ k : Fin 112, orbit step k.val 27 ≤ 9232) := by decide

end ConjectureLab.Collatz
