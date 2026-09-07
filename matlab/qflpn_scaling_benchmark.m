function qflpn_scaling_benchmark()
% ============================================================
% QFLPN SCALING BENCHMARK — MATLAB / MATLAB-COMPATIBLE
% ============================================================
%
% Qubit range:
%     q = 4, ..., 17
%
% State dimensions:
%     N = 2^q
%
% Operator:
%     identical 2x2 unitary rotation blocks
%
% Numerical representation:
%     sparse double
%
% Timing:
%     20 warmup repetitions
%     1000 measured repetitions
%
% Output:
%     matlab/results/qflpn_scaling_matlab.csv
%
% ============================================================

    MIN_QUBITS = 4;
    MAX_QUBITS = 17;

    WARMUP = 20;
    REPETITIONS = 1000;

    TARGET_MS = 15.0;

    MU = 0.70;

    output_dir = fullfile(fileparts(mfilename('fullpath')), 'results');

    if ~exist(output_dir, 'dir')
        mkdir(output_dir);
    end

    output_file = fullfile( ...
        output_dir, ...
        'qflpn_scaling_matlab.csv' ...
    );

    % --------------------------------------------------------
    % QFLPN fuzzy-to-quantum angle
    % --------------------------------------------------------

    if MU < 0 || MU > 1
        error('MU must satisfy 0 <= MU <= 1.');
    end

    theta = 2.0 * asin(sqrt(MU));
    c = cos(theta);
    s = sin(theta);

    % --------------------------------------------------------
    % Console information
    % --------------------------------------------------------

    fprintf('\n');
    fprintf('%s\n', repmat('=', 1, 72));
    fprintf('QFLPN SCALING BENCHMARK - MATLAB / MATLAB-COMPATIBLE\n');
    fprintf('%s\n', repmat('=', 1, 72));
    fprintf('Qubit range          : %d ... %d\n', ...
        MIN_QUBITS, MAX_QUBITS);
    fprintf('Warmup repetitions   : %d\n', WARMUP);
    fprintf('Measured repetitions : %d\n', REPETITIONS);
    fprintf('Fuzzy membership     : %.12f\n', MU);
    fprintf('Rotation angle       : %.12f rad\n', theta);
    fprintf('Target time          : %.6f ms\n', TARGET_MS);
    fprintf('%s\n', repmat('=', 1, 72));

    % --------------------------------------------------------
    % Results table
    % --------------------------------------------------------

    number_of_rows = MAX_QUBITS - MIN_QUBITS + 1;

    language = repmat("MATLAB", number_of_rows, 1);
    qubits = zeros(number_of_rows, 1);
    states = zeros(number_of_rows, 1);
    nnz_values = zeros(number_of_rows, 1);
    repetitions = repmat(REPETITIONS, number_of_rows, 1);
    warmup = repmat(WARMUP, number_of_rows, 1);

    mean_spmv_ms = zeros(number_of_rows, 1);
    median_spmv_ms = zeros(number_of_rows, 1);
    min_spmv_ms = zeros(number_of_rows, 1);
    max_spmv_ms = zeros(number_of_rows, 1);

    maximum_error = zeros(number_of_rows, 1);
    norm_error = zeros(number_of_rows, 1);

    target_ms = repmat(TARGET_MS, number_of_rows, 1);

    numerical_status = strings(number_of_rows, 1);
    timing_status = strings(number_of_rows, 1);

    % --------------------------------------------------------
    % Main scaling loop
    % --------------------------------------------------------

    for row = 1:number_of_rows

        q = MIN_QUBITS + row - 1;
        n = 2^q;

        qubits(row) = q;
        states(row) = n;

        fprintf('\nq=%2d | N=%7d | constructing sparse operator...\n', ...
            q, n);

        % ----------------------------------------------------
        % Construct sparse QFLPN operator.
        %
        % Every pair (2k, 2k+1) receives:
        %
        %     [ c  -s ]
        %     [ s   c ]
        %
        % ----------------------------------------------------

        rows_idx = zeros(2*n, 1);
        cols_idx = zeros(2*n, 1);
        values = zeros(2*n, 1);

        position = 1;

        for k = 1:2:n

            rows_idx(position) = k;
            cols_idx(position) = k;
            values(position) = c;
            position = position + 1;

            rows_idx(position) = k;
            cols_idx(position) = k + 1;
            values(position) = -s;
            position = position + 1;

            rows_idx(position) = k + 1;
            cols_idx(position) = k;
            values(position) = s;
            position = position + 1;

            rows_idx(position) = k + 1;
            cols_idx(position) = k + 1;
            values(position) = c;
            position = position + 1;
        end

        A = sparse( ...
            rows_idx, ...
            cols_idx, ...
            values, ...
            n, ...
            n ...
        );

        nnz_values(row) = nnz(A);

        % ----------------------------------------------------
        % Deterministic normalized input state
        % ----------------------------------------------------

        index = (0:n-1)';

        x = sin(index) + 0.5*cos(0.37*index);

        x_norm = norm(x, 2);

        if x_norm == 0
            error('Input state has zero norm.');
        end

        x = x / x_norm;

        % ----------------------------------------------------
        % Independent analytical reference
        % ----------------------------------------------------

        reference = zeros(n, 1);

        even_index = 1:2:n;
        odd_index = 2:2:n;

        x_even = x(even_index);
        x_odd = x(odd_index);

        reference(even_index) = ...
            c*x_even - s*x_odd;

        reference(odd_index) = ...
            s*x_even + c*x_odd;

        % ----------------------------------------------------
        % Numerical validation
        % ----------------------------------------------------

        y = A*x;

        maximum_error(row) = ...
            max(abs(y - reference));

        input_norm = norm(x, 2);
        output_norm = norm(y, 2);

        norm_error(row) = ...
            abs(output_norm - input_norm);

        if maximum_error(row) <= 1e-12 && ...
                norm_error(row) <= 1e-12
            numerical_status(row) = "PASS";
        else
            numerical_status(row) = "FAIL";
        end

        % ----------------------------------------------------
        % Warmup
        % ----------------------------------------------------

        for w = 1:WARMUP
            y = A*x; %#ok<NASGU>
        end

        % ----------------------------------------------------
        % Timed sparse matrix-vector products
        % ----------------------------------------------------

        timings = zeros(REPETITIONS, 1);

        for r = 1:REPETITIONS

            start_time = tic;

            y = A*x; %#ok<NASGU>

            elapsed_seconds = toc(start_time);

            timings(r) = ...
                elapsed_seconds * 1000.0;
        end

        mean_spmv_ms(row) = mean(timings);
        median_spmv_ms(row) = median(timings);
        min_spmv_ms(row) = min(timings);
        max_spmv_ms(row) = max(timings);

        if mean_spmv_ms(row) <= TARGET_MS
            timing_status(row) = "PASS";
        else
            timing_status(row) = "FAIL";
        end

        fprintf( ...
            ['       nnz=%7d | mean=%.6f ms | ' ...
             'median=%.6f ms | max_error=%.3e | ' ...
             'norm_error=%.3e | %s/%s\n'], ...
            nnz_values(row), ...
            mean_spmv_ms(row), ...
            median_spmv_ms(row), ...
            maximum_error(row), ...
            norm_error(row), ...
            numerical_status(row), ...
            timing_status(row) ...
        );
    end

    % --------------------------------------------------------
    % Build table
    % --------------------------------------------------------

    results = table( ...
        language, ...
        qubits, ...
        states, ...
        nnz_values, ...
        repetitions, ...
        warmup, ...
        mean_spmv_ms, ...
        median_spmv_ms, ...
        min_spmv_ms, ...
        max_spmv_ms, ...
        maximum_error, ...
        norm_error, ...
        target_ms, ...
        numerical_status, ...
        timing_status, ...
        'VariableNames', { ...
            'language', ...
            'qubits', ...
            'states', ...
            'nnz', ...
            'repetitions', ...
            'warmup', ...
            'mean_spmv_ms', ...
            'median_spmv_ms', ...
            'min_spmv_ms', ...
            'max_spmv_ms', ...
            'maximum_error', ...
            'norm_error', ...
            'target_ms', ...
            'numerical_status', ...
            'timing_status' ...
        } ...
    );

    % --------------------------------------------------------
    % Write CSV
    % --------------------------------------------------------

    writetable(results, output_file);

    fprintf('\n');
    fprintf('%s\n', repmat('=', 1, 72));
    fprintf('RESULTS WRITTEN\n');
    fprintf('%s\n', repmat('=', 1, 72));
    fprintf('%s\n', output_file);
    fprintf('%s\n', repmat('=', 1, 72));
    fprintf('\n');

end