import ConjectureLab

open ConjectureLab.ShiftedArrays

example : [0, 1, 2, 3, 4, 5, 6].map count = [1, 4, 16, 62, 235, 888, 3349] := by
  simp only [List.map_cons, List.map_nil, count_eq_walks]
  decide +kernel

#print axioms recurrence
#print axioms generatingFunction
