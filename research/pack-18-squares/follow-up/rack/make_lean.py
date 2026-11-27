"""Emit a kernel check of the closest repaired packing and its side relative to H."""
import json
from pathlib import Path
from fractions import Fraction as F

def rational(n):
    return f'({n.numerator} / {n.denominator} : ℚ)' if n.denominator!=1 else str(n.numerator)
data=json.loads(Path('closest-rational.json').read_text())
rows=[]
for X,Y,T in data['squares']:
    x,y,t=map(F,(X,Y,T))
    c=(1-t*t)/(1+t*t);s=2*t/(1+t*t)
    rows.append('  ⟨'+', '.join(map(rational,(x,y,c,s)))+'⟩')
text='''import ConjectureLab.SquarePacking

/-! Kernel replay for the best repaired finalist of the rack-conditioned search. -/
namespace RackSearch2
open ConjectureLab.SquarePacking

def side : ℚ := '''+rational(F(data['side']))+'\n\n'
text+='def frames : Array Placement := #[\n'+',\n'.join(rows)+'\n]\n\n'
text+='''def witness (i : Fin 18) : Placement := frames[i.val]'(by simp [frames])

theorem feasible : IsPacking (side : ℝ) witness :=
  check_sound (L := side) (by decide +kernel)

theorem strictlyLarger : (7 + Real.sqrt 7) / 2 < (side : ℝ) := by
  have a : (0 : ℚ) < 2 * side - 7 := by decide +kernel
  have b : (7 : ℚ) < (2 * side - 7) ^ 2 := by decide +kernel
  have a' : (0 : ℝ) < 2 * (side : ℝ) - 7 := by exact_mod_cast a
  have b' : (7 : ℝ) < (2 * (side : ℝ) - 7) ^ 2 := by exact_mod_cast b
  have root := Real.sq_sqrt (show (0 : ℝ) ≤ 7 by norm_num)
  apply lt_of_not_ge
  intro h
  have le : 2 * (side : ℝ) - 7 ≤ Real.sqrt 7 := by linarith
  nlinarith only [b', root, mul_self_le_mul_self a'.le le]

#print axioms feasible
#print axioms strictlyLarger
end RackSearch2
'''
Path('RackTrial.lean').write_text(text)
