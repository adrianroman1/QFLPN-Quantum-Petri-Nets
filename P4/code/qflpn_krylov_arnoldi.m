function qflpn_krylov_arnoldi()

Q_MIN = 4;
Q_MAX = 17;

WARMUP = 20;
REPETITIONS = 1000;

FUZZY_MEMBERSHIP = 0.70;
TIME_STEP = 1.0;
KRYLOV_DIMENSION = 20;

TARGET_MS = 15.0;

OUTPUT_DIR = fullfile('matlab', 'results');
OUTPUT_FILE = fullfile(OUTPUT_DIR, ...
    'qflpn_krylov_arnoldi_matlab.csv');

if ~exist(OUTPUT_DIR, 'dir')
    mkdir(OUTPUT_DIR);
end

fprintf('QFLPN KRYLOV-ARNOLDI BENCHMARK - MATLAB / MATLAB-COMPATIBLE\n');
fprintf('Qubit range          : %d ... %d\n', Q_MIN, Q_MAX);
fprintf('Warmup repetitions   : %d\n', WARMUP);
fprintf('Measured repetitions : %d\n', REPETITIONS);
fprintf('Fuzzy membership     : %.12f\n', FUZZY_MEMBERSHIP);
fprintf('Krylov dimension     : %d\n', KRYLOV_DIMENSION);
fprintf('Target time          : %.6f ms\n\n', TARGET_MS);

fid = fopen(OUTPUT_FILE, 'w');

if fid == -1
    error('Unable to open output CSV file.');
end

fprintf(fid, 'language,qubits,states,repetitions,warmup,krylov_dimension,effective_krylov_dimension,mean_arnoldi_ms,median_arnoldi_ms,min_arnoldi_ms,max_arnoldi_ms,target_ms,maximum_error,maximum_norm_error,status\n');

for q = Q_MIN:Q_MAX

    n = 2^q;

    A = build_qflpn_operator(n, FUZZY_MEMBERSHIP);
    x = build_initial_state(n);

    for r = 1:WARMUP
        [~, ~] = arnoldi_exponential_action( ...
            A, x, TIME_STEP, KRYLOV_DIMENSION);
    end

    elapsed_values = zeros(REPETITIONS, 1);
    error_values = zeros(REPETITIONS, 1);
    dimension_values = zeros(REPETITIONS, 1);
    norm_error_values = zeros(REPETITIONS, 1);

    for r = 1:REPETITIONS

        t0 = tic;

        [y, effective_dimension] = ...
            arnoldi_exponential_action( ...
                A, x, TIME_STEP, KRYLOV_DIMENSION);

        elapsed_ms = toc(t0) * 1000.0;

        reference = analytical_exponential_action( ...
            x, FUZZY_MEMBERSHIP, TIME_STEP);

        maximum_absolute_error = ...
            max(abs(y - reference));

        norm_error = ...
            abs(norm(y) - norm(reference));

        elapsed_values(r) = elapsed_ms;
        error_values(r) = maximum_absolute_error;
        dimension_values(r) = effective_dimension;
        norm_error_values(r) = norm_error;
    end

    mean_ms = mean(elapsed_values);
    median_ms = median(elapsed_values);
    min_ms = min(elapsed_values);
    max_ms = max(elapsed_values);

    maximum_error = max(error_values);
    maximum_norm_error = max(norm_error_values);

    effective_dimension = round(median(dimension_values));

    if maximum_error <= 1.0e-12 && ...
       maximum_norm_error <= 1.0e-12 && ...
       mean_ms <= TARGET_MS

        status = 'PASS';

    else

        status = 'FAIL';

    end

    fprintf( ...
        'q=%2d  N=%6d  mean=%.6f ms  median=%.6f ms  max=%.6f ms  K=%2d  error=%.3e  status=%s\n', ...
        q, ...
        n, ...
        mean_ms, ...
        median_ms, ...
        max_ms, ...
        effective_dimension, ...
        maximum_error, ...
        status);

    fprintf( ...
        fid, ...
        'MATLAB,%d,%d,%d,%d,%d,%d,%.12f,%.12f,%.12f,%.12f,%.6f,%.16e,%.16e,%s\n', ...
        q, ...
        n, ...
        REPETITIONS, ...
        WARMUP, ...
        KRYLOV_DIMENSION, ...
        effective_dimension, ...
        mean_ms, ...
        median_ms, ...
        min_ms, ...
        max_ms, ...
        TARGET_MS, ...
        maximum_error, ...
        maximum_norm_error, ...
        status);
end

fclose(fid);

fprintf('\nCSV output: %s\n', OUTPUT_FILE);

end


function A = build_qflpn_operator(n, mu)

if n < 2 || mod(n, 2) ~= 0
    error('The state dimension must be an even positive integer.');
end

theta = 2.0 * asin(sqrt(mu));

c = cos(theta);
s = sin(theta);

rows = zeros(2*n, 1);
cols = zeros(2*n, 1);
values = zeros(2*n, 1);

p = 1;

for k = 1:2:n

    rows(p) = k;
    cols(p) = k;
    values(p) = c;
    p = p + 1;

    rows(p) = k;
    cols(p) = k + 1;
    values(p) = -s;
    p = p + 1;

    rows(p) = k + 1;
    cols(p) = k;
    values(p) = s;
    p = p + 1;

    rows(p) = k + 1;
    cols(p) = k + 1;
    values(p) = c;
    p = p + 1;

end

A = sparse(rows, cols, values, n, n);

end


function x = build_initial_state(n)

x = (1:n)';

x = x / norm(x);

end


function y = analytical_exponential_action(x, mu, time_step)

theta = 2.0 * asin(sqrt(mu));

c = cos(theta);
s = sin(theta);

alpha = exp(time_step * c);
phi = time_step * s;

cp = cos(phi);
sp = sin(phi);

y = zeros(size(x));

even = x(1:2:end);
odd = x(2:2:end);

y(1:2:end) = ...
    alpha .* (cp .* even - sp .* odd);

y(2:2:end) = ...
    alpha .* (sp .* even + cp .* odd);

end


function [y, effective_dimension] = ...
    arnoldi_exponential_action(A, x, time_step, krylov_dimension)

n = length(x);

beta = norm(x);

if beta == 0
    y = zeros(size(x));
    effective_dimension = 0;
    return;
end

m = min(krylov_dimension, n);

V = zeros(n, m);
H = zeros(m, m);

V(:, 1) = x / beta;

effective_dimension = 1;

for j = 1:m

    w = A * V(:, j);

    for i = 1:(j + 1)

        if i <= j
            hij = V(:, i)' * w;
            H(i, j) = H(i, j) + hij;
            w = w - hij * V(:, i);
        end

    end

    for i = 1:j

        hij = V(:, i)' * w;
        H(i, j) = H(i, j) + hij;
        w = w - hij * V(:, i);

    end

    if j >= m

        effective_dimension = m;
        break;

    end

    hnext = norm(w);

    if hnext <= eps * max(1.0, norm(H, 'fro'))

        effective_dimension = j;
        break;

    end

    H(j + 1, j) = hnext;

    V(:, j + 1) = w / hnext;

    effective_dimension = j + 1;

end

H_eff = H(1:effective_dimension, ...
          1:effective_dimension);

V_eff = V(:, 1:effective_dimension);

E = expm(time_step * H_eff);

e1 = zeros(effective_dimension, 1);
e1(1) = beta;

y = V_eff * (E * e1);

end
