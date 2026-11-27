import ConjectureLab.PackingEndpoint
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Ring

/-! The wall-probe cancellation and exchanged row counts in orbit 137.
The input chord bounds concern the actual walls, not the enlarged rack box. -/
namespace Pack18WallProbes
open ConjectureLab.PackingEndpoint

/-- A corner of another nonoverlapping square lies outside the open test
square. If it misses both transverse faces and cannot be behind the square,
it is on or beyond the forward face. -/
theorem forward_face {p t : ℝ} (outside : ¬ (|p| < 1 / 2 ∧ |t| < 1 / 2))
    (notBehind : -(1 / 2) < p) (transverse : |t| < 1 / 2) : 1 / 2 ≤ p := by
  by_contra! h
  exact outside ⟨abs_lt.mpr ⟨notBehind, h⟩, transverse⟩

/-- For a unit middle-frame pair the projected half-width sum is at least
one. Interval tests on the two transverse axes and the reverse directions
then leave only a forward separating axis. Tangency is allowed. -/
theorem separating_choice {c s xu yu xv yv : ℝ} (hc : 0 ≤ c) (circ : c ^ 2 + s ^ 2 = 1)
    (tx : |yu| < 1) (ty : |yv| < 1) (rx : -1 < xu) (ry : -1 < xv)
    (separated : (1 + c+|s|) / 2 ≤ |xu| ∨ (1 + c+|s|) / 2 ≤ |yu| ∨
      (1 + c+|s|) / 2 ≤ |xv| ∨ (1 + c+|s|) / 2 ≤ |yv|) :
    (1 + c+|s|) / 2 ≤ xu ∨ (1 + c+|s|) / 2 ≤ xv := by
  have sq : (1:ℝ) ^ 2 ≤ (c+|s|) ^ 2 := by
    nlinarith only [circ, sq_abs s, mul_nonneg hc (abs_nonneg s)]
  have h := (sq_le_sq₀ (by norm_num : (0:ℝ) ≤ 1) (add_nonneg hc (abs_nonneg s))).mp sq
  rcases separated with h₁ | h₂ | h₃ | h₄
  · by_cases pos : 0 ≤ xu
    · exact Or.inl (by simpa [abs_of_nonneg pos] using h₁)
    · rw [abs_of_neg (lt_of_not_ge pos)] at h₁
      linarith
  · linarith
  · by_cases pos : 0 ≤ xv
    · exact Or.inr (by simpa [abs_of_nonneg pos] using h₃)
    · rw [abs_of_neg (lt_of_not_ge pos)] at h₃
      linarith
  · linarith

noncomputable def halfAngleFrame (t : ℝ) : Vec :=
  ((1 - t ^ 2) / (1 + t ^ 2), (2 * t) / (1 + t ^ 2))

/-- The signed half-angle threshold in the guard, written using the two
parameters used to store the orientation bands. -/
theorem difference_tangent {t v : ℝ} (ht : 0 ≤ t) (hv : 0 ≤ v) :
    dot (halfAngleFrame t) (quarter (halfAngleFrame v)) /
      (1 + dot (halfAngleFrame t) (halfAngleFrame v)) = (t - v) / (1 + t * v) := by
  have h : 0 < 1 + t * v := by positivity
  have a : 0 < 1 + t ^ 2 := by positivity
  have b : 0 < 1 + v ^ 2 := by positivity
  have pos : 0 < 1 + dot (halfAngleFrame t) (halfAngleFrame v) := by
    have e : 1 + dot (halfAngleFrame t) (halfAngleFrame v) =
        2 * (1 + t * v) ^ 2 / ((1 + t ^ 2) * (1 + v ^ 2)) := by
      simp only [dot, halfAngleFrame]
      field_simp
      ring
    rw [e]
    positivity
  apply (div_eq_div_iff pos.ne' h.ne').2
  simp only [dot, quarter, halfAngleFrame]
  field_simp
  ring

/-- Couple two probe offsets so that the slope errors at their shared physical
corner cancel. The counts h and v are the numbers of horizontal/vertical chords. -/
theorem coupled (a b x y ξ η wallX wallY h v slope : ℝ)
    (ha : 0 ≤ a) (hb : 0 ≤ b)
    (vertical : wallY + v + (x - ξ) * slope ≤ y)
    (horizontal : wallX + h - (y - η) * slope ≤ x)
    (coupling : b * (x - ξ) = a * (y - η)) :
    a * (wallX + h) + b * (wallY + v) ≤ a * x + b * y := by
  have cancel := congrArg (fun w : ℝ => w * slope) coupling
  linarith only [mul_le_mul_of_nonneg_left vertical hb,
    mul_le_mul_of_nonneg_left horizontal ha, cancel]

/-- In 137 the horizontal counts are 2+2 and the vertical counts 1+2. -/
theorem combine_corners (w P Q : Vec) (wx wy L : ℝ)
    (near : w.1 * (wx + 2) + w.2 * (wy + 1) ≤ dot w P)
    (far : w.1 * 2 + w.2 * 2 ≤ w.1 * (wx + L - Q.1) + w.2 * (wy + L - Q.2)) :
    dot w (Q - P) ≤ (L - 4) * w.1 + (L - 3) * w.2 := by
  simp only [dot, Prod.fst_sub, Prod.snd_sub] at near ⊢
  linarith only [near, far]

/-- Interchanging coordinates puts the class-137 support bound in the form of
the generic two-unit endpoint inequality. -/
theorem side_from_class137_support (w P Q : Vec) (L : ℝ)
    (unit : dot w w = 1) (large : 4 < L) (two : 2 ≤ dot w (Q - P))
    (walls : dot w (Q - P) ≤ (L - 4) * w.1 + (L - 3) * w.2) :
    (7 + Real.sqrt 7) / 2 ≤ L := by
  apply side_from_support (w.2, w.1) _ large
  · exact (two.trans walls).trans_eq (add_comm _ _)
  · simpa [dot, add_comm] using unit

end Pack18WallProbes

#print axioms Pack18WallProbes.side_from_class137_support
#print axioms Pack18WallProbes.coupled
#print axioms Pack18WallProbes.difference_tangent
#print axioms Pack18WallProbes.separating_choice
