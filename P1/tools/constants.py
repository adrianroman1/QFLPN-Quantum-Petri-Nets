"""Single numerical and instance policy for the P1 CI extension."""

NUMERICAL_TOLERANCE = 1e-12
CANONICAL_MEMBERSHIPS = (0.85, 0.90, 0.45, 0.70)
QUBIT_COUNT = 4
HILBERT_SPACE_DIMENSION = 2 ** QUBIT_COUNT
NUMERIC_DTYPE = "complex128"
REAL_DTYPE = "float64"
BASIS_ORDERING = "big-endian lexicographic"
INITIAL_STATE_LABEL = "|0000>"
OPERATOR_EXPRESSION = "C3X @ (RY(theta_1) kron RY(theta_2) kron RY(theta_3) kron RY(theta_4))"
GATE_SEQUENCE = ["RY(theta_1) on qubit 0", "RY(theta_2) on qubit 1", "RY(theta_3) on qubit 2", "RY(theta_4) on qubit 3", "C3X with controls [0,1,2] and target 3"]
