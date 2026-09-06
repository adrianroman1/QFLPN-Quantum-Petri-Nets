clear;
clc;

% ============================================================
% QFLPN SCALING BENCHMARK
% MATLAB / GNU Octave compatible
%
% Deterministic sparse operator benchmark
% Dimensions: 1024, 10000, 100000
% No random numbers
% No Monte Carlo
% ============================================================

dimensions = [1024, 10000, 100000];

% QFLPN fuzzy membership parameter
mu = 0.70;

% Benchmark parameters
warmup = 20;
repetitions = 1000;

% Timing acceptance threshold
target_ms = 15.0;

% Numerical validation tolerance
error_tolerance = 1e-12;

% Output directory
results_dir = 'results';

if ~exist(results_dir, 'dir')
    mkdir(results_dir);
end

% Output CSV
output_file = fullfile(
    results_dir,
    'qflpn_scaling_matlab.csv'
);

% ============================================================
% QFLPN fuzzy-to-operator mapping
%
% theta = 2 asin(sqrt(mu))
% R(theta) =
% [ cos(theta)  -sin(theta) ]
% [ sin(theta)   cos(theta) ]
%
% Each 2x2 block is unitary/orthogonal.
% ============================================================

theta = 2 * asin(sqrt(mu));

c = cos(theta);
s = sin(theta);

% Results columns:
%
% 1  dimension
% 2  nnz
% 3  mu
% 4  warmup
% 5  repetitions
% 6  construction_ms
% 7  mean_ms
% 8  median_ms
% 9  min_ms
% 10 max_ms
% 11 max_absolute_error
% 12 input_norm
% 13 output_norm
% 14 norm_error
% 15 target_ms
% 16 error_tolerance
% 17 numerical_status
% 18 timing_status

results = zeros(length(dimensions), 18);

% ============================================================
% MAIN BENCHMARK LOOP
% ============================================================

for d = 1:length(dimensions)

    n = dimensions(d);

    fprintf('Running N=%d\n', n);

    % --------------------------------------------------------
    % Validate dimension
    % --------------------------------------------------------

    if mod(n, 2) ~= 0
        error('Dimension N must be even for the 2x2 block operator.');
    end

    % --------------------------------------------------------
    % Sparse matrix construction
    % --------------------------------------------------------

    construction_start = tic;

    % 2 nonzero entries per row
    rows = zeros(2 * n, 1);
    cols = zeros(2 * n, 1);
    values = zeros(2 * n, 1);

    p = 1;

    for k = 1:2:n

        i = k;
        j = k + 1;

        % Row i
        rows(p) = i;
        cols(p) = i;
        values(p) = c;
        p = p + 1;

        rows(p) = i;
        cols(p) = j;
        values(p) = -s;
        p = p + 1;

        % Row j
        rows(p) = j;
        cols(p) = i;
        values(p) = s;
        p = p + 1;

        rows(p) = j;
        cols(p) = j;
        values(p) = c;
        p = p + 1;

    end

    A = sparse(
        rows,
        cols,
        values,
        n,
        n
    );

    construction_ms = toc(construction_start) * 1000.0;

    % --------------------------------------------------------
    % Deterministic input vector
    %
    % No random numbers.
    % No Monte Carlo.
    % --------------------------------------------------------

    index = (0:n-1)';

    x = ...
        sin(index) + ...
        0.5 * cos(0.37 * index);

    % Normalize input vector
    x = x / norm(x);

    % --------------------------------------------------------
    % Independent analytical reference
    %
    % This is NOT calculated with A*x.
    % It provides an independent validation of the
    % sparse matrix-vector multiplication.
    % --------------------------------------------------------

    reference = zeros(n, 1);

    reference(1:2:end) = ...
        c * x(1:2:end) - ...
        s * x(2:2:end);

    reference(2:2:end) = ...
        s * x(1:2:end) + ...
        c * x(2:2:end);

    % --------------------------------------------------------
    % Numerical validation
    % --------------------------------------------------------

    computed = A * x;

    max_absolute_error = ...
        max(abs(computed - reference));

    input_norm = norm(x);

    output_norm = norm(computed);

    norm_error = ...
        abs(output_norm - input_norm);

    % --------------------------------------------------------
    % Numerical status
    % --------------------------------------------------------

    numerical_status = 1;

    if max_absolute_error > error_tolerance
        numerical_status = 0;
    end

    if norm_error > error_tolerance
        numerical_status = 0;
    end

    % --------------------------------------------------------
    % Warm-up
    % --------------------------------------------------------

    for k = 1:warmup
        A * x;
    end

    % --------------------------------------------------------
    % Timed sparse matrix-vector multiplication
    % --------------------------------------------------------

    times_ms = zeros(repetitions, 1);

    for k = 1:repetitions

        timer_start = tic;

        A * x;

        times_ms(k) = ...
            toc(timer_start) * 1000.0;

    end

    % --------------------------------------------------------
    % Timing statistics
    % --------------------------------------------------------

    mean_ms = mean(times_ms);
    median_ms = median(times_ms);
    min_ms = min(times_ms);
    max_ms = max(times_ms);

    % --------------------------------------------------------
    % Timing status
    % --------------------------------------------------------

    timing_status = 1;

    if mean_ms > target_ms
        timing_status = 0;
    end

    % --------------------------------------------------------
    % Store results
    % --------------------------------------------------------

    results(d, :) = [
        n, ...
        nnz(A), ...
        mu, ...
        warmup, ...
        repetitions, ...
        construction_ms, ...
        mean_ms, ...
        median_ms, ...
        min_ms, ...
        max_ms, ...
        max_absolute_error, ...
        input_norm, ...
        output_norm, ...
        norm_error, ...
        target_ms, ...
        error_tolerance, ...
        numerical_status, ...
        timing_status
    ];

    % --------------------------------------------------------
    % Console output
    % --------------------------------------------------------

    fprintf(
        '  NNZ: %d\n',
        nnz(A)
    );

    fprintf(
        '  Construction: %.6f ms\n',
        construction_ms
    );

    fprintf(
        '  Mean: %.6f ms\n',
        mean_ms
    );

    fprintf(
        '  Median: %.6f ms\n',
        median_ms
    );

    fprintf(
        '  Min: %.6f ms\n',
        min_ms
    );

    fprintf(
        '  Max: %.6f ms\n',
        max_ms
    );

    fprintf(
        '  Maximum error: %.3e\n',
        max_absolute_error
    );

    fprintf(
        '  Input norm: %.17g\n',
        input_norm
    );

    fprintf(
        '  Output norm: %.17g\n',
        output_norm
    );

    fprintf(
        '  Norm error: %.3e\n',
        norm_error
    );

    if numerical_status == 1
        fprintf('  Numerical status: PASS\n');
    else
        fprintf('  Numerical status: FAIL\n');
    end

    if timing_status == 1
        fprintf('  Timing status: PASS\n');
    else
        fprintf('  Timing status: FAIL\n');
    end

    fprintf('\n');

end

% ============================================================
% CSV EXPORT
%
% IMPORTANT:
% We intentionally do NOT use table() or writetable().
% GNU Octave used by GitHub Actions does not provide table().
% ============================================================

file_id = fopen(output_file, 'w');

if file_id == -1
    error('Could not open output CSV file for writing.');
end

% ------------------------------------------------------------
% CSV header
% ------------------------------------------------------------

fprintf(
    file_id,
    'language,dimension,nnz,mu,warmup,repetitions,construction_ms,mean_ms,median_ms,min_ms,max_ms,max_absolute_error,input_norm,output_norm,norm_error,target_ms,error_tolerance,numerical_status,timing_status\n'
);

% ------------------------------------------------------------
% CSV data
% ------------------------------------------------------------

for d = 1:length(dimensions)

    n = results(d, 1);
    nnz_value = results(d, 2);
    mu_value = results(d, 3);
    warmup_value = results(d, 4);
    repetitions_value = results(d, 5);

    construction_ms = results(d, 6);
    mean_ms = results(d, 7);
    median_ms = results(d, 8);
    min_ms = results(d, 9);
    max_ms = results(d, 10);

    max_absolute_error = results(d, 11);

    input_norm = results(d, 12);
    output_norm = results(d, 13);

    norm_error = results(d, 14);

    target_value = results(d, 15);
    tolerance_value = results(d, 16);

    numerical_value = results(d, 17);
    timing_value = results(d, 18);

    if numerical_value == 1
        numerical_text = 'PASS';
    else
        numerical_text = 'FAIL';
    end

    if timing_value == 1
        timing_text = 'PASS';
    else
        timing_text = 'FAIL';
    end

    fprintf(
        file_id,
        'MATLAB,%d,%d,%.17g,%d,%d,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%s,%s\n',
        n,
        nnz_value,
        mu_value,
        warmup_value,
        repetitions_value,
        construction_ms,
        mean_ms,
        median_ms,
        min_ms,
        max_ms,
        max_absolute_error,
        input_norm,
        output_norm,
        norm_error,
        target_value,
        tolerance_value,
        numerical_text,
        timing_text
    );

end

fclose(file_id);

% ============================================================
% FINAL MESSAGE
% ============================================================

fprintf(
    'Results saved to:\n%s\n',
    output_file
);