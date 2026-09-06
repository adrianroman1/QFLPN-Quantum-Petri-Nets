function qflpn_reference()
% QFLPN_REFERENCE
% 4-qubit reference implementation of the QFLPN fuzzy-to-quantum mapping.
%
% Declared modeling convention:
%
%     theta(mu) = 2*asin(sqrt(mu))
%
% and therefore:
%
%     RY(theta(mu))*|0>
%
% produces probability mu for |1>.
%
% This script is an independent MATLAB validation of the
% reference mathematical construction.

clc;

% ------------------------------------------------------------
% Reference fuzzy memberships
% ------------------------------------------------------------

mu = [0.85, 0.90, 0.45, 0.70];

nQubits = 4;
stateDimension = 2^nQubits;

% ------------------------------------------------------------
% Fuzzy -> quantum angles
% ------------------------------------------------------------

theta = fuzzy_to_angle(mu);

fprintf('QFLPN 4-qubit reference model\n');
fprintf('------------------------------\n');

fprintf('Number of qubits: %d\n', nQubits);
fprintf('State dimension: %d\n\n', stateDimension);

fprintf('Fuzzy memberships and RY angles:\n');

for k = 1:length(mu)
    fprintf( ...
        'mu = %.6f   theta = %.12f rad\n', ...
        mu(k), ...
        theta(k));
end

% ------------------------------------------------------------
% One-qubit states
% ------------------------------------------------------------

states = cell(1, nQubits);

for k = 1:nQubits

    c = cos(theta(k)/2);
    s = sin(theta(k)/2);

    states{k} = [c; s];

    probabilityOne = abs(states{k}(2))^2;

    fprintf( ...
        'mu = %.6f   P(|1>) = %.12f\n', ...
        mu(k), ...
        probabilityOne);
end

% ------------------------------------------------------------
% Tensor-product construction
% ------------------------------------------------------------

psi = 1;

for k = 1:nQubits
    psi = kron(psi, states{k});
end

% ------------------------------------------------------------
% Normalization
% ------------------------------------------------------------

stateNorm = norm(psi);

fprintf('\nState norm: %.15f\n', stateNorm);

assert( ...
    abs(stateNorm - 1.0) <= 1e-12, ...
    'Reference state is not normalized.');

% ------------------------------------------------------------
% Computational-basis probabilities
% ------------------------------------------------------------

probabilities = abs(psi).^2;

probabilitySum = sum(probabilities);

fprintf('Probability sum: %.15f\n', probabilitySum);

assert( ...
    abs(probabilitySum - 1.0) <= 1e-12, ...
    'Probabilities are not normalized.');

% ------------------------------------------------------------
% Density matrix
% ------------------------------------------------------------

rho = psi * psi';

fprintf('Density matrix size: %d x %d\n', ...
    size(rho,1), size(rho,2));

% Hermiticity check
hermiticityError = norm(rho - rho', 'fro');

fprintf('Hermiticity error: %.15e\n', ...
    hermiticityError);

assert( ...
    hermiticityError <= 1e-12, ...
    'Density matrix is not Hermitian.');

% Trace check
traceError = abs(trace(rho) - 1.0);

fprintf('Trace error: %.15e\n', ...
    traceError);

assert( ...
    traceError <= 1e-12, ...
    'Density matrix does not have unit trace.');

% ------------------------------------------------------------
% Display non-zero computational-basis probabilities
% ------------------------------------------------------------

fprintf('\nComputational-basis probabilities:\n');

for index = 1:length(probabilities)

    if probabilities(index) > 1e-14

        binaryLabel = dec2bin(index - 1, nQubits);

        fprintf( ...
            '|%s> : %.12f\n', ...
            binaryLabel, ...
            probabilities(index));
    end
end

fprintf('\nReference MATLAB validation completed successfully.\n');

end


function theta = fuzzy_to_angle(mu)
% FUZZY_TO_ANGLE
% theta(mu) = 2*asin(sqrt(mu))

if any(mu < 0) || any(mu > 1)
    error( ...
        'Fuzzy memberships must belong to [0,1].');
end

theta = 2 .* asin(sqrt(mu));

end
