% ============================================================
% QFLPN SCALING BENCHMARK - MATLAB / OCTAVE COMPATIBLE
%
% Deterministic sparse/unitary block-rotation operator
%
% q = 4 ... 17
% N = 2^q
% ============================================================

clear;
clc;

% ------------------------------------------------------------
% Configuration
% ------------------------------------------------------------

qubit_min = 4;
qubit_max = 17;

warmup = 20;
repetitions = 1000;

mu = 0.70;
threshold_ms = 15.0;

results_dir = fullfile(fileparts(mfilename('fullpath')), 'results');

if ~exist(results_dir, 'dir')
    mkdir(results_dir);
end

results_file = fullfile(
    results_dir,
    'qflpn_scaling_matlab.csv'
);

% ------------------------------------------------------------
% QFLPN fuzzy-to-rotation convention
% ------------------------------------------------------------

theta = 2.0 * asin(sqrt(mu));

c = cos(theta);
s = sin(theta);

% ------------------------------------------------------------
% Console header
% ------------------------------------------------------------

fprintf('\n');
fprintf('============================================================\n');
fprintf('QFLPN SCALING BENCHMARK - MATLAB / MATLAB-COMPATIBLE\n');
fprintf('============================================================\n');
fprintf('Qubit range          : %d ... %d\n', ...
    qubit_min, qubit_max);
fprintf('State range          : %d ... %d\n', ...
    2^qubit_min, 2^qubit_max);
fprintf('Warmup repetitions   : %d\n', warmup);
fprintf('Measured repetitions : %d\n', repetitions);
fprintf('Fuzzy membership     : %.12f\n', mu);
fprintf('Rotation angle       : %.12f rad\n', theta);
fprintf('Target time          : %.6f ms\n', threshold_ms);
fprintf('\n');

% ------------------------------------------------------------
% CSV file
% ------------------------------------------------------------

fid = fopen(results_file, 'w');

if fid == -1
    error('Cannot open result file for writing.');
end

fprintf(fid, ...
    ['language,qubits,states,nnz,warmup,repetitions,' ...
     'fuzzy_membership,rotation_angle_rad,' ...
     'mean_state_ms,median_state_ms,min_state_ms,max_state_ms,' ...
     'maximum_error,norm_preservation_error,target_ms,' ...
     'numerical_status,timing_status\n']);

% ------------------------------------------------------------
% Scaling loop
% ------------------------------------------------------------

for q = qubit_min:qubit_max

    n = 2^q;

    fprintf( ...
        'q=%2d | N=%6d | NNZ=%7d | ', ...
        q, n, 2*n);

    % --------------------------------------------------------
    % Deterministic normalized state
    % --------------------------------------------------------

    idx = (1:n)';

    x = sin(idx) + 0.5*cos(0.37*idx);

    x_norm = norm(x, 2);

    if x_norm == 0
        fclose(fid);
        error('Invalid zero input state.');
    end

    x = x / x_norm;

    % --------------------------------------------------------
    % Sparse block-rotation operator
    % --------------------------------------------------------

    construction_start = tic;

    blocks = n / 2;

    base = (0:blocks-1)'*2 + 1;

    rows = [
        base;
        base;
        base + 1;
        base + 1
    ];

    cols = [
        base;
        base + 1;
        base;
        base + 1
    ];

    vals = [
        c*ones(blocks,1);
        -s*ones(blocks,1);
        s*ones(blocks,1);
        c*ones(blocks,1)
    ];

    A = sparse(
        rows,
        cols,
        vals,
        n,
        n
    );

    construction_ms = toc(construction_start) * 1000.0;

    % --------------------------------------------------------
    % Independent analytical reference
    % --------------------------------------------------------

    y_ref = zeros(n,1);

    y_ref(1:2:end) = ...
        c*x(1:2:end) - s*x(2:2:end);

    y_ref(2:2:end) = ...
        s*x(1:2:end) + c*x(2:2:end);

    % --------------------------------------------------------
    % Warmup
    % --------------------------------------------------------

    for r = 1:warmup
        y = A*x;
    end

    % --------------------------------------------------------
    % Measured sparse matrix-vector operations
    % --------------------------------------------------------

    times_ms = zeros(repetitions,1);

    for r = 1:repetitions

        t0 = tic;

        y = A*x;

        times_ms(r) = toc(t0) * 1000.0;

    end

    % --------------------------------------------------------
    % Metrics
    % --------------------------------------------------------

    mean_ms = mean(times_ms);
    median_ms = median(times_ms);
    min_ms = min(times_ms);
    max_ms = max(times_ms);

    maximum_error = max(abs(y - y_ref));

    norm_preservation_error = ...
        abs(norm(y,2) - 1.0);

    % --------------------------------------------------------
    % Numerical status
    % --------------------------------------------------------

    numerical_ok = ...
        isfinite(maximum_error) && ...
        isfinite(norm_preservation_error) && ...
        maximum_error <= 1e-12 && ...
        norm_preservation_error <= 1e-12;

    if numerical_ok
        numerical_status = 'PASS';
    else
        numerical_status = 'FAIL';
    end

    % --------------------------------------------------------
    % Timing status
    % --------------------------------------------------------

    timing_ok = ...
        isfinite(mean_ms) && ...
        mean_ms <= threshold_ms;

    if timing_ok
        timing_status = 'PASS';
    else
        timing_status = 'FAIL';
    end

    % --------------------------------------------------------
    % Console output
    % --------------------------------------------------------

    fprintf( ...
        'mean=%.6f ms | median=%.6f ms | ' ...
        'maxerr=%.3e | normerr=%.3e | ' ...
        'build=%.3f ms | %s/%s\n', ...
        mean_ms, ...
        median_ms, ...
        maximum_error, ...
        norm_preservation_error, ...
        construction_ms, ...
        numerical_status, ...
        timing_status);

    % --------------------------------------------------------
    % CSV output
    % --------------------------------------------------------

    fprintf( ...
        fid, ...
        ['MATLAB,%d,%d,%d,%d,%d,%.12f,%.12f,' ...
         '%.9f,%.9f,%.9f,%.9f,%.16e,%.16e,%.6f,%s,%s\n'], ...
        q, ...
        n, ...
        2*n, ...
        warmup, ...
        repetitions, ...
        mu, ...
        theta, ...
        mean_ms, ...
        median_ms, ...
        min_ms, ...
        max_ms, ...
        maximum_error, ...
        norm_preservation_error, ...
        threshold_ms, ...
        numerical_status, ...
        timing_status);

end

% ------------------------------------------------------------
% Close CSV
% ------------------------------------------------------------

fclose(fid);

fprintf('\n');
fprintf('============================================================\n');
fprintf('Results written to:\n');
fprintf('%s\n', results_file);
fprintf('============================================================\n');
fprintf('\n');