module

public import ConjectureLab.SquarePacking
public import Mathlib.Analysis.SpecialFunctions.Trigonometric.Bounds
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.LinearCombination
import Mathlib.Tactic.Ring

/-! # Certificates excluding insertion near a reference packing

Each leaf supplies a point which stays in one perturbed open tile and is
strictly within half a unit of every possible free centre in that box.
-/

@[expose] public section
namespace ConjectureLab.InsertionCover
open ConjectureLab.SquarePacking (Placement)

structure Box where
  xmin : ℚ
  xmax : ℚ
  ymin : ℚ
  ymax : ℚ
  deriving Repr

inductive Tree where
  | leaf (i : Fin 17) (a b : ℚ)
  | vertical (left right : Tree)
  | horizontal (low high : Tree)

def initial : Box := ⟨1/2, 97/20 - 1/2, 1/2, 97/20 - 1/2⟩
def midX (r : Box) : ℚ := (r.xmin + r.xmax) / 2
def midY (r : Box) : ℚ := (r.ymin + r.ymax) / 2
def far (lo hi w : ℚ) : ℚ := max |lo - w| |hi - w|

def leafCheck (p : Placement) (a b : ℚ) (r : Box) : Bool :=
  let u := a*p.c - b*p.s
  let v := a*p.s + b*p.c
  let margin := (1/32 : ℚ) * (|u| + |v| + 3/2)
  decide (p.c^2 + p.s^2 = 1 ∧
    |u*p.c + v*p.s| + margin < 1/2 ∧ |u*(-p.s) + v*p.c| + margin < 1/2 ∧
    (far r.xmin r.xmax (p.x+u))^2 + (far r.ymin r.ymax (p.y+v))^2 < 1/4)

def checkTree (p : Fin 17 → Placement) : Tree → Box → Bool
  | .leaf i a b, r => leafCheck (p i) a b r
  | .vertical l h, r =>
    checkTree p l {r with xmax := midX r} && checkTree p h {r with xmin := midX r}
  | .horizontal l h, r =>
    checkTree p l {r with ymax := midY r} && checkTree p h {r with ymin := midY r}

def check (p : Fin 17 → Placement) (t : Tree) : Bool := checkTree p t initial

structure Pose where
  x : ℝ
  y : ℝ
  c : ℝ
  s : ℝ

def UnitFrame (p : Pose) : Prop := p.c^2 + p.s^2 = 1

def Close (r : Placement) (p : Pose) : Prop :=
  |p.x - (r.x : ℝ)| ≤ 1/32 ∧ |p.y - (r.y : ℝ)| ≤ 1/32 ∧
  |p.c - (r.c : ℝ)| ≤ 1/32 ∧ |p.s - (r.s : ℝ)| ≤ 1/32

/-- Moving by at most 1/32 radians changes each component of the frame by
at most 1/32. The squares may choose their perturbations independently. -/
theorem close_of_angle_bound (r : Placement) (p : Pose) (oldAngle newAngle : ℝ)
    (ox : (r.c : ℝ) = Real.cos oldAngle) (oy : (r.s : ℝ) = Real.sin oldAngle)
    (nx : p.c = Real.cos newAngle) (ny : p.s = Real.sin newAngle)
    (hx : |p.x - (r.x : ℝ)| ≤ 1/32) (hy : |p.y - (r.y : ℝ)| ≤ 1/32)
    (ha : |newAngle - oldAngle| ≤ 1/32) : Close r p := by
  refine ⟨hx, hy, ?_, ?_⟩
  · rw [nx, ox]
    exact (Real.abs_cos_sub_cos_le _ _).trans ha
  · rw [ny, oy]
    exact (Real.abs_sin_sub_sin_le _ _).trans ha

def OpenTile (p : Pose) : Set (ℝ × ℝ) :=
  {z | ∃ a b : ℝ, |a| < 1/2 ∧ |b| < 1/2 ∧
    (p.x + a*p.c - b*p.s, p.y + a*p.s + b*p.c) = z}

def InBox (r : Box) (x y : ℝ) : Prop :=
  (r.xmin : ℝ) ≤ x ∧ x ≤ (r.xmax : ℝ) ∧ (r.ymin : ℝ) ≤ y ∧ y ≤ (r.ymax : ℝ)

private theorem interior {p : Pose} (h : UnitFrame p) (x y : ℝ)
    (hx : |(x-p.x)*p.c + (y-p.y)*p.s| < 1/2)
    (hy : |(x-p.x)*(-p.s) + (y-p.y)*p.c| < 1/2) : (x,y) ∈ OpenTile p := by
  unfold UnitFrame at h
  refine ⟨_, _, hx, hy, Prod.ext ?_ ?_⟩
  · dsimp
    linear_combination (x-p.x)*h
  · dsimp
    linear_combination (y-p.y)*h

private theorem disk_interior {p : Pose} (h : UnitFrame p) (x y : ℝ)
    (hd : (x-p.x)^2 + (y-p.y)^2 < 1/4) : (x,y) ∈ OpenTile p := by
  let a := (x-p.x)*p.c + (y-p.y)*p.s
  let b := (x-p.x)*(-p.s) + (y-p.y)*p.c
  have eq : a^2 + b^2 = (x-p.x)^2 + (y-p.y)^2 := by
    dsimp [a,b]
    unfold UnitFrame at h
    linear_combination ((x-p.x)^2 + (y-p.y)^2)*h
  apply interior h x y
  · change |a| < 1/2
    apply (sq_lt_sq₀ (abs_nonneg a) (by norm_num : (0 : ℝ) ≤ 1/2)).mp
    rw [sq_abs]
    nlinarith only [hd, eq, sq_nonneg b]
  · change |b| < 1/2
    apply (sq_lt_sq₀ (abs_nonneg b) (by norm_num : (0 : ℝ) ≤ 1/2)).mp
    rw [sq_abs]
    nlinarith only [hd, eq, sq_nonneg a]

private theorem norm_one_le (c s : ℝ) (h : c^2 + s^2 = 1) : |c| + |s| ≤ 3/2 := by
  have sqle : (|c| + |s|)^2 ≤ 2 := by
    nlinarith only [h, sq_abs c, sq_abs s, sq_nonneg (|c| - |s|)]
  nlinarith only [sqle, sq_nonneg (|c| + |s| - 3/2)]

private theorem weighted_error {e f : ℝ} (he : |e| ≤ 1/32) (hf : |f| ≤ 1/32) (x y : ℝ) :
    |e*x + f*y| ≤ (1/32)*(|x| + |y|) := by
  calc
    _ ≤ |e*x| + |f*y| := abs_add_le _ _
    _ ≤ _ := by
      rw [abs_mul, abs_mul, mul_add]
      exact add_le_add (mul_le_mul_of_nonneg_right he (abs_nonneg _))
        (mul_le_mul_of_nonneg_right hf (abs_nonneg _))

private theorem robust {u v dx dy c s C S : ℝ}
    (hx : |dx| ≤ 1/32) (hy : |dy| ≤ 1/32)
    (hc : |C-c| ≤ 1/32) (hs : |S-s| ≤ 1/32)
    (frame : C^2 + S^2 = 1) :
    |(u+dx)*C + (v+dy)*S| ≤ |u*c+v*s| + (1/32)*(|u|+|v|+3/2) := by
  have orient := weighted_error hc hs u v
  have trans := weighted_error hx hy C S
  have size := norm_one_le C S frame
  calc
    _ = |(u*c+v*s) + ((C-c)*u+(S-s)*v) + (dx*C+dy*S)| := by congr 1; ring
    _ ≤ |(u*c+v*s) + ((C-c)*u+(S-s)*v)| + |dx*C+dy*S| := abs_add_le _ _
    _ ≤ _ := by linarith only [abs_add_le (u*c+v*s) ((C-c)*u+(S-s)*v), orient, trans, size]

private theorem far_bound {lo hi w : ℚ} {x : ℝ} (hl : (lo:ℝ) ≤ x) (hr : x ≤ (hi:ℝ)) :
    (x - (w:ℝ))^2 ≤ (far lo hi w : ℝ)^2 := by
  have e : |x-(w:ℝ)| ≤ max |(lo:ℝ)-w| |(hi:ℝ)-w| := by
    apply abs_le.mpr
    constructor
    · linarith only [hl, neg_abs_le ((lo:ℝ)-w), le_max_left |(lo:ℝ)-w| |(hi:ℝ)-w|]
    · linarith only [hr, le_abs_self ((hi:ℝ)-w), le_max_right |(lo:ℝ)-w| |(hi:ℝ)-w|]
  have esq := (sq_le_sq₀ (abs_nonneg _) ((abs_nonneg _).trans e)).mpr e
  simpa [far, sq_abs] using esq

private theorem leaf_sound (r : Box) (q : Placement) (a b : ℚ) (fixed free : Pose)
    (hf : UnitFrame fixed) (hn : Close q fixed) (hu : UnitFrame free)
    (inside : InBox r free.x free.y) (verified : leafCheck q a b r = true) :
    ∃ z, z ∈ OpenTile fixed ∧ z ∈ OpenTile free := by
  let u := a*q.c-b*q.s
  let v := a*q.s+b*q.c
  let x := q.x+u
  let y := q.y+v
  change decide (_ ∧ _ ∧ _ ∧ _) = true at verified
  obtain ⟨_, ha, hb, hd⟩ := of_decide_eq_true verified
  change |u*q.c + v*q.s| + (1/32:ℚ)*(|u|+|v|+3/2) < 1/2 at ha
  change |u*(-q.s) + v*q.c| + (1/32:ℚ)*(|u|+|v|+3/2) < 1/2 at hb
  change (far r.xmin r.xmax x)^2 + (far r.ymin r.ymax y)^2 < 1/4 at hd
  obtain ⟨hx0,hx1,hy0,hy1⟩ := inside
  obtain ⟨hcx,hcy,hcc,hcs⟩ := hn
  have dx : |(q.x:ℝ)-fixed.x| ≤ 1/32 := by rwa [abs_sub_comm]
  have dy : |(q.y:ℝ)-fixed.y| ≤ 1/32 := by rwa [abs_sub_comm]
  have ex : (x:ℝ) - fixed.x = (u:ℝ) + ((q.x:ℝ)-fixed.x) := by dsimp [x]; push_cast; ring
  have ey : (y:ℝ) - fixed.y = (v:ℝ) + ((q.y:ℝ)-fixed.y) := by dsimp [y]; push_cast; ring
  refine ⟨((x:ℝ),(y:ℝ)), interior hf _ _ ?_ ?_, disk_interior hu _ _ ?_⟩
  · rw [ex,ey]
    apply lt_of_le_of_lt (robust dx dy hcc hcs hf)
    have hx := (Rat.cast_lt (K := ℝ)).2 ha
    push_cast at hx
    exact hx
  · rw [ex,ey]
    have nc : |-fixed.s - (-(q.s:ℝ))| ≤ 1/32 := by
      rw [show -fixed.s - (-(q.s:ℝ)) = -(fixed.s - (q.s:ℝ)) by ring, abs_neg]
      exact hcs
    have hrot : (-fixed.s)^2 + fixed.c^2 = 1 := by simpa [UnitFrame, add_comm] using hf
    apply lt_of_le_of_lt (robust dx dy nc hcc hrot)
    have hx := (Rat.cast_lt (K := ℝ)).2 hb
    push_cast at hx
    exact hx
  · have hdx := far_bound (w:=x) hx0 hx1
    have hdy := far_bound (w:=y) hy0 hy1
    have hdist : (far r.xmin r.xmax x:ℝ)^2 + (far r.ymin r.ymax y:ℝ)^2 < 1/4 := by
      have hx := (Rat.cast_lt (K := ℝ)).2 hd
      push_cast at hx
      exact hx
    nlinarith only [hdx,hdy,hdist]

theorem checkTree_sound {p : Fin 17 → Placement} (moving : Fin 17 → Pose)
    (frame : ∀ i, UnitFrame (moving i)) (near : ∀ i, Close (p i) (moving i))
    (free : Pose) (unitFree : UnitFrame free) (t : Tree) (r : Box)
    (verified : checkTree p t r = true) (inside : InBox r free.x free.y) :
    ∃ i z, z ∈ OpenTile (moving i) ∧ z ∈ OpenTile free := by
  induction t generalizing r with
  | leaf i a b =>
    exact ⟨i,leaf_sound r (p i) a b (moving i) free (frame i) (near i) unitFree inside verified⟩
  | vertical l h il ih =>
    obtain ⟨pl,ph⟩ := Bool.and_eq_true_iff.mp verified
    obtain ⟨x0,x1,y0,y1⟩ := inside
    by_cases mid : free.x ≤ (midX r:ℝ)
    · exact il _ pl ⟨x0,mid,y0,y1⟩
    · exact ih _ ph ⟨(le_of_not_ge mid),x1,y0,y1⟩
  | horizontal l h il ih =>
    obtain ⟨pl,ph⟩ := Bool.and_eq_true_iff.mp verified
    obtain ⟨x0,x1,y0,y1⟩ := inside
    by_cases mid : free.y ≤ (midY r:ℝ)
    · exact il _ pl ⟨x0,x1,y0,mid⟩
    · exact ih _ ph ⟨x0,x1,(le_of_not_ge mid),y1⟩

theorem check_sound {p : Fin 17 → Placement} {t : Tree} (verified : check p t = true)
    (moving : Fin 17 → Pose) (frame : ∀ i, UnitFrame (moving i))
    (near : ∀ i, Close (p i) (moving i)) (free : Pose)
    (unitFree : UnitFrame free) (inside : InBox initial free.x free.y) :
    ∃ i z, z ∈ OpenTile (moving i) ∧ z ∈ OpenTile free :=
  checkTree_sound moving frame near free unitFree t initial verified inside

/-- Every point of the free closed square belongs to the container [0,L]². -/
def Contained (L : ℝ) (p : Pose) : Prop :=
  ∀ a b : ℝ, |a| ≤ 1/2 → |b| ≤ 1/2 →
    0 ≤ p.x + a*p.c - b*p.s ∧ p.x + a*p.c - b*p.s ≤ L ∧
    0 ≤ p.y + a*p.s + b*p.c ∧ p.y + a*p.s + b*p.c ≤ L

theorem centre_in_box {L : ℝ} {p : Pose} (unit : UnitFrame p)
    (size : L ≤ 97/20) (h : Contained L p) : InBox initial p.x p.y := by
  unfold UnitFrame at unit
  have hc : |p.c / 2| ≤ 1/2 := by
    rw [abs_div, abs_of_nonneg (by norm_num : (0 : ℝ) ≤ 2)]
    have hc1 : |p.c| ≤ 1 := by
      apply (sq_le_sq₀ (abs_nonneg _) zero_le_one).mp
      rw [sq_abs]
      nlinarith only [unit, sq_nonneg p.s]
    linarith
  have hs : |p.s / 2| ≤ 1/2 := by
    rw [abs_div, abs_of_nonneg (by norm_num : (0 : ℝ) ≤ 2)]
    have hs1 : |p.s| ≤ 1 := by
      apply (sq_le_sq₀ (abs_nonneg _) zero_le_one).mp
      rw [sq_abs]
      nlinarith only [unit, sq_nonneg p.c]
    linarith
  have east := (h (p.c/2) (-(p.s/2)) hc (by rwa [abs_neg])).2.1
  have west := (h (-(p.c/2)) (p.s/2) (by rwa [abs_neg]) hs).1
  have north := (h (p.s/2) (p.c/2) hs hc).2.2.2
  have south := (h (-(p.s/2)) (-(p.c/2)) (by rwa [abs_neg]) (by rwa [abs_neg])).2.2.1
  unfold InBox initial
  norm_num
  exact ⟨by nlinarith only [west,unit], by nlinarith only [east,unit,size],
    by nlinarith only [south,unit], by nlinarith only [north,unit,size]⟩

theorem collision_of_contained {p : Fin 17 → Placement} {t : Tree} (verified : check p t = true)
    (moving : Fin 17 → Pose) (frame : ∀ i, UnitFrame (moving i))
    (near : ∀ i, Close (p i) (moving i)) (free : Pose) (unitFree : UnitFrame free)
    {L : ℝ} (size : L ≤ 97/20) (inside : Contained L free) :
    ∃ i z, z ∈ OpenTile (moving i) ∧ z ∈ OpenTile free :=
  check_sound verified moving frame near free unitFree (centre_in_box unitFree size inside)

end ConjectureLab.InsertionCover
