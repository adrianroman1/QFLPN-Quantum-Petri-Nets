"""
all_python.py
Pachet redus care conține exemplul PennyLane pentru o tranziție simplificată a unui mic Petri cuantic hibrid.
"""
import pennylane as qml
from pennylane import numpy as np

# Device de exemplu — folosiți un backend real sau simulator specializat în producție
dev = qml.device("default.qubit", wires=3)

@qml.qnode(dev)
def quantum_petri_transition(fuzzy_membership_angle):
    """Aplica un set de porți care modelează o tranziție simplificată în QFLPN.

    Args:
        fuzzy_membership_angle (float): unghiul derivat din funcția de apartenență fuzzy.

    Returns:
        state (np.ndarray): vectorul de stare complex al sistemului cu 3 qubiți.
    """
    # Qubit 0: Loc P1, Qubit 1: Loc P2, Qubit 2: Oracol / flag deadlock
    qml.RY(fuzzy_membership_angle, wires=0)
    qml.Hadamard(wires=1)
    qml.CNOT(wires=[0, 1])
    # Toffoli (CCX) — necesita pluginul corespunzator daca nu este suportat nativ
    qml.Toffoli(wires=[0, 1, 2])
    return qml.state()


if __name__ == "__main__":
    angle = np.pi / 4
    state = quantum_petri_transition(angle)
    print("Starea finală a sistemului (vector de stare):")
    print(state)
