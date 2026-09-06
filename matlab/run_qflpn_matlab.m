function run_qflpn_matlab()
% RUN_QFLPN_MATLAB
%
% Deterministic MATLAB QFLPN experiment.
%
% Measures:
%   - state construction time
%   - density matrix construction time
%   - total execution time
%   - numerical error
%
% The 15 ms value is an experimental target threshold.
% It is NOT assumed to be achieved before measurement.
%
% Results are exported to CSV for later thesis tables/figures.
%
% No Monte Carlo.

clc;

fprintf('\n');
fprintf('============================================================\n');
fprintf('QFLPN MATLAB EXPERIMENT\n');
fprintf('============================================================\n');

% ------------------------------------------------------------
% Reference configuration
% ------------------------------------------------------------

mu = [0.85, 0.90, 0.45, 0.70];

target_ms = 15.0;

% Fixed deterministic number of repetitions.
% This is NOT Monte Carlo sampling.
num_repetitions = 1000;

fprintf('\nReference memberships:\n');
fprintf('[%.2f %.2f %.2f %.2f]\n', mu);

fprintf('\nTarget execution time: %.3f ms\n', target_ms);
fprintf('Deterministic repetitions: %d\n', num_repetitions);

% ------------------------------------------------------------
% Warm-up
% ------------------------------------------------------------

for k = 1:20
    [psi, rho, theta] = qflpn_quantum_core(mu); %#ok<ASGLU>
end

% ------------------------------------------------------------
% Timed experiment
% ------------------------------------------------------------

state_times = zeros(num_repetitions, 1);
density_times = zeros(num_repetitions, 1);
total_times = zeros(num_repetitions, 1);

for k = 1:num_repetitions

    t_total = tic;

    t_state = tic;

    [psi, ~, theta] = qflpn_quantum_core(mu); %#ok<ASGLU>

    state_times(k) = toc(t_state);

    t_density = tic;

    rho = psi * psi';

    density_times(k) = toc(t_density);

    total_times(k) = toc(t_total);

end

% ------------------------------------------------------------
% Convert to milliseconds
% ------------------------------------------------------------

state_ms = state_times * 1000.0;
density_ms = density_times * 1000.0;
total_ms = total_times * 1000.0;

% ------------------------------------------------------------
% Statistics
% ------------------------------------------------------------

mean_state_ms = mean(state_ms);
mean_density_ms = mean(density_ms);
mean_total_ms = mean(total_ms);

min_total_ms = min(total_ms);
max_total_ms = max(total_ms);
median_total_ms = median(total_ms);

% ------------------------------------------------------------
% Numerical validation
% ------------------------------------------------------------

normalization_error = abs(norm(psi) - 1.0);

probability_error = abs( ...
    sum(abs(psi).^2) - 1.0 ...
);

hermiticity_error = norm( ...
    rho - rho', ...
    'fro' ...
);

trace_error = abs(trace(rho) - 1.0);

fidelity_error = abs( ...
    abs(psi' * psi)^2 - 1.0 ...
);

maximum_error = max([ ...
    normalization_error, ...
    probability_error, ...
    hermiticity_error, ...
    trace_error, ...
    fidelity_error ...
]);

% ------------------------------------------------------------
% Output
% ------------------------------------------------------------

fprintf('\n============================================================\n');
fprintf('TIMING RESULTS\n');
fprintf('============================================================\n');

fprintf( ...
    'Mean state construction      : %.6f ms\n', ...
    mean_state_ms);

fprintf( ...
    'Mean density matrix          : %.6f ms\n', ...
    mean_density_ms);

fprintf( ...
    'Mean total execution         : %.6f ms\n', ...
    mean_total_ms);

fprintf( ...
    'Median total execution       : %.6f ms\n', ...
    median_total_ms);

fprintf( ...
    'Minimum total execution      : %.6f ms\n', ...
    min_total_ms);

fprintf( ...
    'Maximum total execution      : %.6f ms\n', ...
    max_total_ms);

fprintf('\n============================================================\n');
fprintf('NUMERICAL VALIDATION\n');
fprintf('============================================================\n');

fprintf( ...
    'Maximum numerical error      : %.3e\n', ...
    maximum_error);

if maximum_error <= 1e-12
    fprintf('Numerical status              : PASS\n');
else
    fprintf('Numerical status              : REVIEW REQUIRED\n');
end

fprintf('\n============================================================\n');
fprintf('15 ms TARGET\n');
fprintf('============================================================\n');

if mean_total_ms <= target_ms
    fprintf( ...
        'Mean execution %.6f ms <= %.3f ms : PASS\n', ...
        mean_total_ms, ...
        target_ms);
else
    fprintf( ...
        'Mean execution %.6f ms > %.3f ms : TARGET NOT MET\n', ...
        mean_total_ms, ...
        target_ms);
end

% ------------------------------------------------------------
% CSV export
% ------------------------------------------------------------

results = table( ...
    num_repetitions, ...
    mean_state_ms, ...
    mean_density_ms, ...
    mean_total_ms, ...
    median_total_ms, ...
    min_total_ms, ...
    max_total_ms, ...
    target_ms, ...
    maximum_error, ...
    'VariableNames', { ...
        'repetitions', ...
        'mean_state_ms', ...
        'mean_density_ms', ...
        'mean_total_ms', ...
        'median_total_ms', ...
        'min_total_ms', ...
        'max_total_ms', ...
        'target_ms', ...
        'maximum_error' ...
    } ...
);

output_file = 'qflpn_matlab_results.csv';

writetable(results, output_file);

fprintf('\nResults exported to:\n%s\n', ...
    fullfile(pwd, output_file));

fprintf('\nQFLPN MATLAB experiment completed.\n\n');

end
