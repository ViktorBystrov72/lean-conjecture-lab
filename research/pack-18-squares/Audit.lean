import ConjectureLab.SquarePacking

open ConjectureLab.SquarePacking

-- A horizontal contact with no common interior point.
def touching (i : Fin 2) : Placement :=
  ⟨(i.val : ℚ) + 1 / 2, 1 / 2, 1, 0⟩

example : check 2 touching = true := by decide +kernel
example : IsPacking 2 touching := check_sound (L := (2 : ℚ)) (by decide +kernel)

-- A positive overlap of width 1/1000000 must be rejected.
example : check 2 (fun i : Fin 2 => ⟨(i.val : ℚ) * 999999 / 1000000 + 1/2, 1/2, 1, 0⟩) = false := by decide +kernel

-- A rational rotation with both projections strictly larger than a unit.
def rotated (_ : Fin 1) : Placement := fromSlope (7/10) (7/10) (1/2)
example : check (7/5) rotated = true := by decide +kernel
example : check (13999/10000) rotated = false := by decide +kernel
example : check 100 (fun _ : Fin 1 => ⟨1, 1, 0, 0⟩) = false := by decide +kernel

def grid (i : Fin 18) : Placement := ⟨(i.val % 6 : ℕ) + (1/2 : ℚ), (i.val / 6 : ℕ) + (1/2 : ℚ), 1, 0⟩
example : check 6 grid = true := by decide +kernel
example : improves18 6 grid = false := by decide +kernel

#print axioms check_sound
#print axioms improves18_sound
#print axioms point_distance_sq
