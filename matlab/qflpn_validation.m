function qflpn_validation()
% QFLPN_VALIDATION
%
% Independent MATLAB validation of the 4-qubit QFLPN reference model.
%
% Validates:
%   1. fuzzy -> quantum mapping
%   2. state normalization
%   3. probability conservation
%   4. density matrix Hermiticity
%   5. density matrix trace
%   6. self-fidelity
%   7. numerical error
%
% No Monte Carlo.
% Fixed deterministic reference instance.

clc;

fprintf('\n');
fprintf('============================================================\n');
fprintf('QFLPN MATLAB VALIDATION\n');
fprintf('============================================================\n');

% ------------------------------------------------------------
% Reference instance
% ------------------------------------------------------------

mu = [0.85, 0.90, 0.45, 0.70];

fprintf('\nReference fuzzy memberships:\n');
fprintf('mu = [%.2f %.2f %.2f %.2f]\n', mu);

% ------------------------------------------------------------
% Core model
% ------------------------------------------------------------

[psi, rho, theta] = qflpn_quantum_core(mu);

% ------------------------------------------------------------
% 1. Fuzzy -> quantum mapping
% ------------------------------------------------------------

mapping_errors = zeros(1, 4);

fprintf('\n[1] Fuzzy -> quantum mapping\n');

for k = 1:4

    probability_one = abs( ...
        cos(theta(k)/2) ...
    )^2;

    % The above expression is P(|0>), therefore P(|1>) is:
    probability_one = abs( ...
        sin(theta(k)/2) ...
    )^2;

    mapping_errors(k) = ...
        abs(probability_one - mu(k));

    fprintf( ...
        'mu(%d)=%.6f | P(|1>)=%.12f | error=%.3e\n', ...
        k, ...
        mu(k), ...
        probability_one, ...
        mapping_errors(k));
end

max_mapping_error = max(mapping_errors);

% ------------------------------------------------------------
% 2. State normalization
% ------------------------------------------------------------

state_norm = norm(psi);
normalization_error = abs(state_norm - 1.0);

fprintf('\n[2] State normalization\n');
fprintf('||psi|| = %.15f\n', state_norm);
fprintf('error   = %.3e\n', normalization_error);

% ------------------------------------------------------------
% 3. Probability conservation
% ------------------------------------------------------------

probabilities = abs(psi).^2;
probability_sum = sum(probabilities);
probability_error = abs(probability_sum - 1.0);

fprintf('\n[3] Probability conservation\n');
fprintf('sum(P)  = %.15f\n', probability_sum);
fprintf('error   = %.3e\n', probability_error);

% ------------------------------------------------------------
% 4. Density matrix Hermiticity
% ------------------------------------------------------------

hermiticity_error = norm( ...
    rho - rho', ...
    'fro' ...
);

fprintf('\n[4] Density matrix Hermiticity\n');
fprintf('error   = %.3e\n', hermiticity_error);

% ------------------------------------------------------------
% 5. Density matrix trace
% ------------------------------------------------------------

trace_value = trace(rho);
trace_error = abs(trace_value - 1.0);

fprintf('\n[5] Density matrix trace\n');
fprintf('trace   = %.15f\n', real(trace_value));
fprintf('error   = %.3e\n', trace_error);

% ------------------------------------------------------------
% 6. Self fidelity
% ------------------------------------------------------------

fidelity = abs(psi' * psi)^2;
fidelity_error = abs(fidelity - 1.0);

fprintf('\n[6] Self-fidelity\n');
fprintf('F       = %.15f\n', fidelity);
fprintf('error   = %.3e\n', fidelity_error);

% ------------------------------------------------------------
% Global numerical error
% ------------------------------------------------------------

maximum_error = max([ ...
    max_mapping_error, ...
    normalization_error, ...
    probability_error, ...
    hermiticity_error, ...
    trace_error, ...
    fidelity_error ...
]);

fprintf('\n============================================================\n');
fprintf('VALIDATION SUMMARY\n');
fprintf('============================================================\n');

fprintf( ...
    'Maximum numerical error = %.3e\n', ...
    maximum_error);

if maximum_error <= 1e-12
    fprintf('STATUS = PASS\n');
else
    fprintf('STATUS = REVIEW REQUIRED\n');
end

fprintf('============================================================\n\n');

end
