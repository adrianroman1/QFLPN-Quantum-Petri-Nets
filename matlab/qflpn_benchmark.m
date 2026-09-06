function qflpn_benchmark()
% QFLPN_BENCHMARK
%
% Deterministic MATLAB benchmark for the 4-qubit
% QFLPN reference model.
%
% Measures:
%   - state construction time
%   - total execution time
%   - numerical validation error
%
% Exports:
%   qflpn_matlab_results.csv
%
% No Monte Carlo.
%
% IMPORTANT:
% qflpn_quantum_core is executed with verbose=false
% during timing so console output is not included
% in the measured execution time.

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
warmup = 20;
targetMs = 15.0;

% ------------------------------------------------------------
% Warm-up
% ------------------------------------------------------------

for k = 1:warmup

    [psi, ~, ~] = qflpn_quantum_core(mu, false);

end

% ------------------------------------------------------------
% Timed benchmark
% ------------------------------------------------------------

stateTimes = zeros(repetitions,1);
totalTimes = zeros(repetitions,1);

for k = 1:repetitions

    totalTimer = tic;

    stateTimer = tic;

    [psi, ~, ~] = qflpn_quantum_core(mu, false);

    stateTimes(k) = toc(stateTimer) * 1000.0;

    % Density matrix construction is part of total execution.
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

traceError = abs( ...
    trace(rho) - 1.0);

maximumError = max([ ...
    normalizationError, ...
    probabilityError, ...
    fidelityError, ...
    hermiticityError, ...
    traceError]);

% ------------------------------------------------------------
% Status
% ------------------------------------------------------------

if maximumError <= 1e-12
    numericalStatus = "PASS";
else
    numericalStatus = "REVIEW REQUIRED";
end

if meanTotalMs <= targetMs
    timingStatus = "PASS";
else
    timingStatus = "TARGET NOT MET";
end

% ------------------------------------------------------------
% Console output
% ------------------------------------------------------------

fprintf('\nReference model:\n');
fprintf('  qubits            : %d\n', nQubits);
fprintf('  states            : %d\n', nStates);
fprintf('  repetitions       : %d\n', repetitions);
fprintf('  warm-up           : %d\n', warmup);

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
fprintf('  status            : %s\n', numericalStatus);

fprintf('\n15 ms target:\n');
fprintf('  status            : %s\n', timingStatus);

% ------------------------------------------------------------
% CSV export
% ------------------------------------------------------------

fid = fopen( ...
    'qflpn_matlab_results.csv', ...
    'w');

if fid == -1
    error('Unable to create qflpn_matlab_results.csv');
end

fprintf(fid, ...
    ['language,qubits,states,repetitions,warmup,' ...
     'mean_state_ms,median_state_ms,min_state_ms,max_state_ms,' ...
     'mean_total_ms,median_total_ms,min_total_ms,max_total_ms,' ...
     'target_ms,maximum_error,numerical_status,timing_status\n']);

fprintf(fid, ...
    ['MATLAB,%d,%d,%d,%d,' ...
     '%.12f,%.12f,%.12f,%.12f,' ...
     '%.12f,%.12f,%.12f,%.12f,' ...
     '%.6f,%.12e,%s,%s\n'], ...
    nQubits, ...
    nStates, ...
    repetitions, ...
    warmup, ...
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
    numericalStatus, ...
    timingStatus);

fclose(fid);

fprintf('\nCSV exported:\n');
fprintf('  qflpn_matlab_results.csv\n');

fprintf('\nQFLPN MATLAB benchmark completed.\n\n');

end