module

public import Mathlib.Analysis.Real.Sqrt
public import Mathlib.Basic.Sign.Basic
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.LinearCombination
import Mathlib.Tactic.Ring

/-! # The two-face endpoint inequality for 18-square packing

This independently formalizes the geometric implication in the “Two native
separating faces” section of Mira Cult's 18-square packing argument. A caller
must still certify the endpoint supports, separation and transverse guard for
every physical configuration in its branch. -/

@[expose] public section
namespace ConjectureLab.PackingEndpoint
open SignType (sign)

abbrev Vec := ℝ × ℝ

def dot (a b : Vec) : ℝ := a.1 * b.1 + a.2 * b.2

def quarter (a : Vec) : Vec := (-a.2, a.1)

private theorem dot_swap (a b : Vec) : dot a b = dot b a := by
  unfold dot
  ring

private theorem oriented_swap (a b : Vec) : dot b (quarter a) = -dot a (quarter b) := by
  simp [dot, quarter]
  ring

private theorem expand_in_frame (a b x : Vec) (hb : dot b b = 1) :
    dot a x = dot a b * dot b x + dot a (quarter b) * dot (quarter b) x := by
  simp only [dot, quarter] at hb ⊢
  linear_combination -(a.1 * x.1 + a.2 * x.2) * hb

private theorem unit_pair (u v : Vec) (hu : dot u u = 1) (hv : dot v v = 1) :
    (dot u v) ^ 2 + (dot u (quarter v)) ^ 2 = 1 := by
  simp only [dot, quarter] at hu hv ⊢
  linear_combination (u.1 * u.1 + u.2 * u.2) * hv + hu

private theorem split_path (w p f g q : Vec) :
    dot w (q - p) = dot w (f - p) + dot w (g - f) + dot w (q - g) := by
  simp [dot]
  ring

/-- The signed half-angle guard pays the loss 1 − c from unequal normals,
including the case s = 0 where the guard has no premise to verify. -/
theorem transverse_bound {c s z : ℝ} (hc : 0 < c) (circle : c ^ 2 + s ^ 2 = 1)
    (guard : s ≠ 0 → |s| / (1 + c) ≤ 1 / 2 + (sign s : ℝ) * z) :
    1 - c ≤ |s|/2 + s * z := by
  have h : |s| * (|s| / (1 + c)) ≤ |s| * (1 / 2 + (sign s : ℝ) * z) := by
    by_cases hs : s = 0
    · simp [hs]
    · exact mul_le_mul_of_nonneg_left (guard hs) (abs_nonneg _)
  have angle : |s| * |s| / (1 + c) = 1 - c := by
    apply (div_eq_iff (by linarith : 1 + c ≠ 0)).2
    nlinarith only [sq_abs s, circle]
  calc
    1 - c = |s| * (|s| / (1 + c)) := by rw [← angle]; ring
    _ ≤ |s| * (1 / 2 + (sign s : ℝ) * z) := h
    _ = |s|/2 + s * z := by rw [mul_add, ← mul_assoc, abs_mul_sign]; ring

section Faces
variable {u v P F G Q : Vec}
local notation "cosUV" => dot u v
local notation "sinUV" => dot u (quarter v)

/-- Project the three consecutive gaps on the first tile's forward normal. -/
theorem first_face_bridge (hu : dot u u = 1) (hv : dot v v = 1) (positive : 0 < cosUV)
    (front : 1 / 2 ≤ dot u (F - P)) (back : 1 / 2 ≤ dot v (Q - G))
    (separating : (1 + cosUV + |sinUV|) / 2 ≤ dot u (G - F))
    (guard : sinUV ≠ 0 → |sinUV| / (1 + cosUV) ≤
      1 / 2 + (sign sinUV : ℝ) * dot (quarter v) (Q - G)) :
    2 ≤ dot u (Q - P) := by
  have cross := transverse_bound positive (unit_pair u v hu hv) guard
  have along := mul_le_mul_of_nonneg_left back positive.le
  rw [split_path u P F G Q, expand_in_frame u v (Q - G) hv]
  linarith only [front, separating, cross, along]

/-- Project on the second normal. The transverse coordinate changes sign. -/
theorem second_face_bridge (hu : dot u u = 1) (hv : dot v v = 1) (positive : 0 < cosUV)
    (front : 1 / 2 ≤ dot u (F - P)) (back : 1 / 2 ≤ dot v (Q - G))
    (separating : (1 + cosUV + |sinUV|) / 2 ≤ dot v (G - F))
    (guard : sinUV ≠ 0 → |sinUV| / (1 + cosUV) ≤
      1 / 2 - (sign sinUV : ℝ) * dot (quarter u) (F - P)) :
    2 ≤ dot v (Q - P) := by
  have cross := transverse_bound (z := -dot (quarter u) (F - P)) positive
    (unit_pair u v hu hv) (fun hs => by simpa only [mul_neg, sub_eq_add_neg] using guard hs)
  have along := mul_le_mul_of_nonneg_left front positive.le
  rw [split_path v P F G Q, expand_in_frame v u (F - P) hu, dot_swap v u, oriented_swap u v]
  linarith only [back, separating, cross, along]
end Faces

/-- A support of length at least two under the wall-row bound forces the
claimed side. Here L > 4 is an explicit hypothesis. -/
theorem side_from_support {L : ℝ} (w : Vec) (unit : dot w w = 1) (large : 4 < L)
    (support : 2 ≤ (L - 3) * w.1 + (L - 4) * w.2) : (7 + Real.sqrt 7) / 2 ≤ L := by
  let a := L - 3
  let b := L - 4
  have orthogonal :
      (a * w.1 + b * w.2) ^ 2 + (a * w.2 - b * w.1) ^ 2 = a ^ 2 + b ^ 2 := by
    calc
      _ = (a ^ 2 + b ^ 2) * dot w w := by unfold dot; ring
      _ = _ := by rw [unit, mul_one]
  have magnitude : (2 : ℝ) ^ 2 ≤ (a * w.1 + b * w.2) ^ 2 :=
    (sq_le_sq₀ (by norm_num) (by dsimp [a, b]; linarith)).2 support
  have rad : (2 * L - 7) ^ 2 ≥ 7 := by
    dsimp [a, b] at orthogonal magnitude
    nlinarith only [orthogonal, magnitude, sq_nonneg ((L - 3) * w.2 - (L - 4) * w.1)]
  have root : Real.sqrt 7 ≤ 2 * L - 7 := by
    apply (sq_le_sq₀ (Real.sqrt_nonneg _) (by linarith)).mp
    rwa [Real.sq_sqrt (by norm_num : (0:ℝ) ≤ 7)]
  linarith only [root]

section Endpoint
variable {u v P F G Q : Vec} {L : ℝ}
local notation "cosUV" => dot u v
local notation "sinUV" => dot u (quarter v)

/-- Conditional terminal theorem. The disjunction supplies a genuine
separating axis and its signed transverse guard for this very configuration. -/
theorem side_from_two_faces (hu : dot u u = 1) (hv : dot v v = 1) (positive : 0 < cosUV)
    (front : 1 / 2 ≤ dot u (F - P)) (back : 1 / 2 ≤ dot v (Q - G))
    (choice :
      ((1 + cosUV + |sinUV|) / 2 ≤ dot u (G - F) ∧
        (sinUV ≠ 0 → |sinUV|/(1 + cosUV) ≤ 1 / 2 + (sign sinUV : ℝ) * dot (quarter v) (Q - G))) ∨
      ((1 + cosUV + |sinUV|) / 2 ≤ dot v (G - F) ∧
        (sinUV ≠ 0 → |sinUV|/(1 + cosUV) ≤ 1 / 2 - (sign sinUV : ℝ) * dot (quarter u) (F - P))))
    (large : 4 < L)
    (upperU : dot u (Q - P) ≤ (L - 3) * u.1 + (L - 4) * u.2)
    (upperV : dot v (Q - P) ≤ (L - 3) * v.1 + (L - 4) * v.2) :
    (7 + Real.sqrt 7) / 2 ≤ L := by
  rcases choice with ⟨separating, guard⟩ | ⟨separating, guard⟩
  · exact side_from_support u hu large
      ((first_face_bridge hu hv positive front back separating guard).trans upperU)
  · exact side_from_support v hv large
      ((second_face_bridge hu hv positive front back separating guard).trans upperV)
end Endpoint

section Chord

/-- In the coordinates of a middle tile, its two faces are at x = ±1/2.
The determinant inequality puts the ordinate of the entire intervening line
strictly between its two transverse faces, including at the face crossings. -/
theorem inside_chord_strip {dx dy k x y : ℝ}
    (guard : |dy| + 2 * |k| < dx) (line : dx * y = k + dy * x)
    (strip : |x| ≤ 1 / 2) : |y| < 1 / 2 := by
  have positive : 0 < dx := by linarith [abs_nonneg dy, abs_nonneg k]
  have h : dx * |y| ≤ |k| + |dy| * (1 / 2) := by
    calc
      dx * |y| = |dx * y| := by rw [abs_mul, abs_of_pos positive]
      _ = |k + dy * x| := by rw [line]
      _ ≤ |k| + |dy * x| := abs_add_le _ _
      _ ≤ |k| + |dy| * (1 / 2) := by
        rw [abs_mul]
        exact add_le_add_right (mul_le_mul_of_nonneg_left strip (abs_nonneg dy)) _
  by_contra! outside
  have := mul_le_mul_of_nonneg_left outside positive.le
  linarith

/-- The corner at the start is outside the open middle tile and its normal
coordinate is below the far face. The end corner satisfies the reversed test.
Consequently the segment crosses both full face levels, with contact allowed. -/
theorem crosses_both_faces {dx dy k px py qx qy : ℝ}
    (guard : |dy| + 2 * |k| < dx)
    (pLine : dx * py = k + dy * px) (qLine : dx * qy = k + dy * qx)
    (pOutside : ¬ (|px| < 1 / 2 ∧ |py| < 1 / 2))
    (qOutside : ¬ (|qx| < 1 / 2 ∧ |qy| < 1 / 2))
    (pBefore : px < 1 / 2) (qAfter : -(1 / 2) < qx) :
    px ≤ -(1 / 2) ∧ 1 / 2 ≤ qx := by
  constructor
  · by_contra! hp
    have hs := abs_lt.mpr ⟨hp, pBefore⟩
    exact pOutside ⟨hs, inside_chord_strip guard pLine hs.le⟩
  · by_contra! hq
    have hs := abs_lt.mpr ⟨qAfter, hq⟩
    exact qOutside ⟨hs, inside_chord_strip guard qLine hs.le⟩

/-- Two unit-wide chords on one segment with disjoint interiors give
a segment of length at least two. The variables are distances from its start. -/
theorem two_chords_length {a b c d length : ℝ}
    (ha : 0 ≤ a) (hc : 0 ≤ c) (hb : b ≤ length) (hd : d ≤ length)
    (width₁ : 1 ≤ b - a) (width₂ : 1 ≤ d - c) (disjoint : b ≤ c ∨ d ≤ a) :
    2 ≤ length := by
  rcases disjoint with order | order <;> linarith

end Chord

end ConjectureLab.PackingEndpoint
