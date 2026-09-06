function qflpn_benchmark()
% QFLPN_BENCHMARK
%
% Deterministic MATLAB benchmark for the 4-qubit
% QFLPN reference model.
%
% Outputs:
%   qflpn_matlab_results.csv
%
% Measures:
%   - state construction time
%   - total execution time
%   - normalization error
%   - probability error
%   - fidelity error
%
% No Monte Carlo.

clc;

fprintf('\n');
fprintf('============================================================\n');
fprintf('QFLPN MATLAB BENCHMARK\n');
fprintf('============================================================\n');

% ------------------------------------------------------------
% Configuration
% ------------------------------------------------------------

mu = [0.85, 0.90, 0.45, 0.70];

nQubits = 4;
nStates = 2^nQubits;

repetitions = 1000;
targetMs = 15.0;

% ------------------------------------------------------------
% Warm-up
% ------------------------------------------------------------

for k = 1:20

    [psi, ~, ~] = qflpn_quantum_core(mu);

    rho = psi * psi'; %#ok<NASGU>

end

% ------------------------------------------------------------
% Timed benchmark
% ------------------------------------------------------------

stateTimes = zeros(repetitions,1);
totalTimes = zeros(repetitions,1);

for k = 1:repetitions

    totalTimer = tic;

    stateTimer = tic;

    [psi, ~, ~] = qflpn_quantum_core(mu);

    stateTimes(k) = toc(stateTimer) * 1000.0;

    rho = psi * psi';

    totalTimes(k) = toc(totalTimer) * 1000.0;

end

% ------------------------------------------------------------
% Timing statistics
% ------------------------------------------------------------

meanStateMs = mean(stateTimes);
medianStateMs = median(stateTimes);
minStateMs = min(stateTimes);
maxStateMs = max(stateTimes);

meanTotalMs = mean(totalTimes);
medianTotalMs = median(totalTimes);
minTotalMs = min(totalTimes);
maxTotalMs = max(totalTimes);

% ------------------------------------------------------------
% Numerical validation
% ------------------------------------------------------------

normalizationError = abs(norm(psi) - 1.0);

probabilityError = abs( ...
    sum(abs(psi).^2) - 1.0);

fidelityError = abs( ...
    abs(psi' * psi)^2 - 1.0);

hermiticityError = norm( ...
    rho - rho', ...
    'fro');

maximumError = max([ ...
    normalizationError, ...
    probabilityError, ...
    fidelityError, ...
    hermiticityError]);

% ------------------------------------------------------------
% Status
% ------------------------------------------------------------

if meanTotalMs <= targetMs
    status = "PASS";
else
    status = "TARGET NOT MET";
end

% ------------------------------------------------------------
% Console output
% ------------------------------------------------------------

fprintf('\nQubits              : %d\n', nQubits);
fprintf('States              : %d\n', nStates);
fprintf('Repetitions         : %d\n', repetitions);

fprintf('\nState construction:\n');
fprintf('  mean              : %.6f ms\n', meanStateMs);
fprintf('  median            : %.6f ms\n', medianStateMs);
fprintf('  min               : %.6f ms\n', minStateMs);
fprintf('  max               : %.6f ms\n', maxStateMs);

fprintf('\nTotal execution:\n');
fprintf('  mean              : %.6f ms\n', meanTotalMs);
fprintf('  median            : %.6f ms\n', medianTotalMs);
fprintf('  min               : %.6f ms\n', minTotalMs);
fprintf('  max               : %.6f ms\n', maxTotalMs);

fprintf('\nNumerical validation:\n');
fprintf('  maximum error     : %.3e\n', maximumError);

fprintf('\n15 ms target:\n');
fprintf('  STATUS            : %s\n', status);

% ------------------------------------------------------------
% CSV export
% ------------------------------------------------------------

T = table( ...
    "MATLAB", ...
    nQubits, ...
    nStates, ...
    repetitions, ...
    meanStateMs, ...
    medianStateMs, ...
    minStateMs, ...
    maxStateMs, ...
    meanTotalMs, ...
    medianTotalMs, ...
    minTotalMs, ...
    maxTotalMs, ...
    targetMs, ...
    maximumError, ...
    status, ...
    'VariableNames', { ...
        'language', ...
        'qubits', ...
        'states', ...
        'repetitions', ...
        'mean_state_ms', ...
        'median_state_ms', ...
        'min_state_ms', ...
        'max_state_ms', ...
        'mean_total_ms', ...
        'median_total_ms', ...
        'min_total_ms', ...
        'max_total_ms', ...
        'target_ms', ...
        'maximum_error', ...
        'status' ...
    });

outputFile = 'qflpn_matlab_results.csv';

writetable(T, outputFile);

fprintf('\nCSV exported: %s\n', ...
    fullfile(pwd, outputFile));

fprintf('\nQFLPN MATLAB benchmark completed.\n\n');

end
