module

public import Mathlib.Analysis.Real.Sqrt
import Mathlib.Tactic.FieldSimp
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.LinearCombination
import Mathlib.Tactic.Ring

/-! # Exact certificates for packings of unit squares

Input coordinates are rational. All geometric conclusions concern the real plane.
Boundary contacts are allowed. The support in a direction is calculated in
doubled coordinates to avoid half-lengths in the checker.
-/

@[expose] public section
namespace ConjectureLab.SquarePacking

structure Placement where
  x : ℚ
  y : ℚ
  c : ℚ
  s : ℚ
  deriving DecidableEq

/-- Rational centre and half-angle tangent. The other chart is unnecessary for
squares, since rotating a square through a half turn preserves its image. -/
def fromSlope (x y t : ℚ) : Placement :=
  ⟨x, y, (1 - t ^ 2) / (1 + t ^ 2), 2 * t / (1 + t ^ 2)⟩

theorem fromSlope_unit (x y t : ℚ) :
    (fromSlope x y t).c ^ 2 + (fromSlope x y t).s ^ 2 = 1 := by
  have hd : 1 + t ^ 2 ≠ 0 := by nlinarith [sq_nonneg t]
  unfold fromSlope
  dsimp
  field_simp [hd]
  ring

abbrev Axis := ℚ × ℚ

def centre (p : Placement) (a : Axis) : ℚ := 2 * (a.1 * p.x + a.2 * p.y)
def along (p : Placement) (a : Axis) : ℚ := a.1 * p.c + a.2 * p.s
def across (p : Placement) (a : Axis) : ℚ := -a.1 * p.s + a.2 * p.c
def radius (p : Placement) (a : Axis) : ℚ := |along p a| + |across p a|

def horizontal : Axis := (1, 0)
def vertical : Axis := (0, 1)

def fitsAxis (L : ℚ) (p : Placement) (a : Axis) : Bool :=
  decide (radius p a ≤ centre p a ∧ centre p a + radius p a ≤ 2 * L)

def fits (L : ℚ) (p : Placement) : Bool :=
  decide (p.c ^ 2 + p.s ^ 2 = 1) && fitsAxis L p horizontal && fitsAxis L p vertical

def before (p q : Placement) (a : Axis) : Bool :=
  decide (0 < radius p a ∧ centre p a + radius p a ≤ centre q a - radius q a)

def directions (p : Placement) : List Axis :=
  [(p.c, p.s), (-p.s, p.c), (-p.c, -p.s), (p.s, -p.c)]

def separated (p q : Placement) : Bool :=
  (directions p ++ directions q).any (before p q)

/-- Check orthonormality, containment and a separating axis for each pair. -/
def check {n : ℕ} (L : ℚ) (p : Fin n → Placement) : Bool :=
  decide ((∀ i, fits L (p i) = true) ∧
    (∀ i j, i < j → separated (p i) (p j) = true))

/-- Check a strict improvement of the 18-square record using rational arithmetic. -/
def improves18 (L : ℚ) (p : Fin 18 → Placement) : Bool :=
  check L p && decide (0 < L ∧ (2 * L - 7 < 0 ∨ (2 * L - 7) ^ 2 < 7))

/-- The local coordinates u,v are measured in half-side lengths. -/
noncomputable def point (p : Placement) (u v : ℝ) : ℝ × ℝ :=
  (p.x + (p.c * u - p.s * v) / 2, p.y + (p.s * u + p.c * v) / 2)

def closedSquare (p : Placement) : Set (ℝ × ℝ) :=
  {z | ∃ u v : ℝ, |u| ≤ 1 ∧ |v| ≤ 1 ∧ point p u v = z}

def openSquare (p : Placement) : Set (ℝ × ℝ) :=
  {z | ∃ u v : ℝ, |u| < 1 ∧ |v| < 1 ∧ point p u v = z}

/-- Explicit Euclidean metric identity. In particular each side has length 1. -/
theorem point_distance_sq (p : Placement) (hp : p.c ^ 2 + p.s ^ 2 = 1) (u v u' v' : ℝ) :
    ((point p u v).1 - (point p u' v').1) ^ 2 +
      ((point p u v).2 - (point p u' v').2) ^ 2 =
      ((u - u') ^ 2 + (v - v') ^ 2) / 4 := by
  have h : (p.c : ℝ) ^ 2 + (p.s : ℝ) ^ 2 = 1 := by exact_mod_cast hp
  unfold point
  dsimp
  linear_combination h * (((u - u') ^ 2 + (v - v') ^ 2) / 4)

def project (a : Axis) (z : ℝ × ℝ) : ℝ := 2 * (a.1 * z.1 + a.2 * z.2)

private theorem project_formula (p : Placement) (a : Axis) (u v : ℝ) :
    project a (point p u v) - (centre p a : ℝ) =
      u * (along p a : ℝ) + v * (across p a : ℝ) := by
  simp only [project, point, centre, along, across]
  push_cast
  ring

private theorem project_abs (p : Placement) (a : Axis) (u v : ℝ) :
    |project a (point p u v) - (centre p a : ℝ)| ≤ max |u| |v| * (radius p a : ℝ) := by
  rw [project_formula]
  have hr : (radius p a : ℝ) = |(along p a : ℝ)| + |(across p a : ℝ)| := by
    simp [radius]
  rw [hr, mul_add]
  apply (abs_add_le _ _).trans
  rw [abs_mul, abs_mul]
  exact add_le_add (mul_le_mul_of_nonneg_right (le_max_left _ _) (abs_nonneg _))
    (mul_le_mul_of_nonneg_right (le_max_right _ _) (abs_nonneg _))

private theorem closed_bounds {p : Placement} {a : Axis} {z : ℝ × ℝ} (hz : z ∈ closedSquare p) :
    (centre p a : ℝ) - (radius p a : ℝ) ≤ project a z ∧
      project a z ≤ (centre p a : ℝ) + (radius p a : ℝ) := by
  obtain ⟨u, v, hu, hv, rfl⟩ := hz
  have hr : 0 ≤ (radius p a : ℝ) := by
    have h : 0 ≤ radius p a := add_nonneg (abs_nonneg _) (abs_nonneg _)
    exact_mod_cast h
  have h := (project_abs p a u v).trans (mul_le_mul_of_nonneg_right (max_le hu hv) hr)
  rw [one_mul, abs_le] at h
  constructor <;> linarith

private theorem contained_axis {L : ℚ} {p : Placement} (a : Axis)
    (hf : fitsAxis L p a = true) {z : ℝ × ℝ} (hz : z ∈ closedSquare p) :
    0 ≤ project a z ∧ project a z ≤ 2 * (L : ℝ) := by
  obtain ⟨lower, upper⟩ := of_decide_eq_true hf
  have hl : (radius p a : ℝ) ≤ (centre p a : ℝ) := by exact_mod_cast lower
  have hu : (centre p a : ℝ) + (radius p a : ℝ) ≤ 2 * (L : ℝ) := by exact_mod_cast upper
  obtain ⟨lo, hi⟩ := closed_bounds (a := a) hz
  constructor <;> linarith

private theorem disjoint_of_before {p q : Placement} {a : Axis} (hf : before p q a = true) :
    Disjoint (openSquare p) (openSquare q) := by
  obtain ⟨positive, gap⟩ := of_decide_eq_true hf
  have hp : 0 < (radius p a : ℝ) := by exact_mod_cast positive
  have hg : (centre p a : ℝ) + (radius p a : ℝ) ≤ (centre q a : ℝ) - (radius q a : ℝ) := by
    exact_mod_cast gap
  apply Set.disjoint_left.mpr
  rintro _ ⟨u, v, hu, hv, rfl⟩ ⟨u', v', hu', hv', he⟩
  have hleft := (project_abs p a u v).trans_lt (mul_lt_mul_of_pos_right (max_lt hu hv) hp)
  rw [one_mul, abs_lt] at hleft
  have hright := (closed_bounds (a := a) (p := q) ⟨u', v', hu'.le, hv'.le, he⟩).1
  linarith

/-- A geometric packing in [0,L] × [0,L], allowing boundary contact. -/
def IsPacking {n : ℕ} (L : ℝ) (p : Fin n → Placement) : Prop :=
  (∀ i, ((p i).c : ℝ) ^ 2 + ((p i).s : ℝ) ^ 2 = 1) ∧
  (∀ i, ∀ z ∈ closedSquare (p i), 0 ≤ z.1 ∧ z.1 ≤ L ∧ 0 ≤ z.2 ∧ z.2 ≤ L) ∧
  (∀ i j, i ≠ j → Disjoint (openSquare (p i)) (openSquare (p j)))

theorem check_sound {n : ℕ} {L : ℚ} {p : Fin n → Placement} (h : check L p = true) :
    IsPacking (L : ℝ) p := by
  obtain ⟨inside, pairs⟩ := of_decide_eq_true h
  simp only [fits, Bool.and_eq_true, decide_eq_true_eq] at inside
  refine ⟨fun i => ?_, fun i z hz => ?_, fun i j hij => ?_⟩
  · exact_mod_cast (inside i).1.1
  · have hx := contained_axis horizontal (inside i).1.2 hz
    have hy := contained_axis vertical (inside i).2 hz
    simp only [project, horizontal, vertical, Rat.cast_one, Rat.cast_zero,
      one_mul, zero_mul, add_zero, zero_add] at hx hy
    exact ⟨by linarith, by linarith, by linarith, by linarith⟩
  · have ordered (i j : Fin n) (hlt : i < j) : Disjoint (openSquare (p i)) (openSquare (p j)) := by
      obtain ⟨a, _, hap⟩ := List.any_eq_true.mp (pairs i j hlt)
      exact disjoint_of_before hap
    rcases lt_or_gt_of_ne hij with hlt | hgt
    · exact ordered i j hlt
    · exact (ordered j i hgt).symm

theorem improves18_sound {L : ℚ} {p : Fin 18 → Placement} (h : improves18 L p = true) :
    IsPacking (L : ℝ) p ∧ 0 < (L : ℝ) ∧ (L : ℝ) < (7 + Real.sqrt 7) / 2 := by
  simp only [improves18, Bool.and_eq_true, decide_eq_true_eq] at h
  refine ⟨check_sound h.1, by exact_mod_cast h.2.1, ?_⟩
  have hr := Real.sqrt_nonneg 7
  have hs := Real.sq_sqrt (show (0 : ℝ) ≤ 7 by norm_num)
  rcases h.2.2 with below | short
  · have hb : 2 * (L : ℝ) - 7 < 0 := by exact_mod_cast below
    linarith
  · have hb : (2 * (L : ℝ) - 7) ^ 2 < 7 := by exact_mod_cast short
    by_contra! hbad
    have hcmp : Real.sqrt 7 ≤ 2 * (L : ℝ) - 7 := by linarith
    nlinarith [mul_self_le_mul_self hr hcmp]

end ConjectureLab.SquarePacking
