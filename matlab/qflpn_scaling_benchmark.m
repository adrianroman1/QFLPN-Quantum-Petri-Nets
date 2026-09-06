clear;
clc;

dimensions = [1024, 10000, 100000];

mu = 0.70;

warmup = 20;
repetitions = 1000;

target_ms = 15.0;
error_tolerance = 1e-12;

results_dir = "results";

if ~exist(results_dir, "dir")
    mkdir(results_dir);
end

output_file = fullfile(
    results_dir,
    "qflpn_scaling_matlab.csv"
);

theta = 2 * asin(sqrt(mu));

c = cos(theta);
s = sin(theta);

results = zeros(
    length(dimensions),
    10
);

for d = 1:length(dimensions)

    n = dimensions(d);

    fprintf("Running N=%d\n", n);

    construction_start = tic;

    rows = zeros(2*n, 1);
    cols = zeros(2*n, 1);
    values = zeros(2*n, 1);

    p = 1;

    for k = 1:2:n

        i = k;
        j = k + 1;

        rows(p) = i;
        cols(p) = i;
        values(p) = c;
        p = p + 1;

        rows(p) = i;
        cols(p) = j;
        values(p) = -s;
        p = p + 1;

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

    construction_ms = ...
        toc(construction_start) * 1000.0;

    index = (0:n-1)';

    x = ...
        sin(index) + ...
        0.5 * cos(0.37 * index);

    x = x / norm(x);

    reference = zeros(n, 1);

    reference(1:2:end) = ...
        c * x(1:2:end) - ...
        s * x(2:2:end);

    reference(2:2:end) = ...
        s * x(1:2:end) + ...
        c * x(2:2:end);

    computed = A * x;

    max_absolute_error = ...
        max(abs(computed - reference));

    input_norm = norm(x);

    output_norm = norm(computed);

    norm_error = ...
        abs(output_norm - input_norm);

    for k = 1:warmup
        A * x;
    end

    times_ms = zeros(
        repetitions,
        1
    );

    for k = 1:repetitions

        timer_start = tic;

        A * x;

        times_ms(k) = ...
            toc(timer_start) * 1000.0;

    end

    mean_ms = mean(times_ms);
    median_ms = median(times_ms);
    min_ms = min(times_ms);
    max_ms = max(times_ms);

    numerical_status = "PASS";

    if ...
        max_absolute_error > error_tolerance ...
        || norm_error > error_tolerance

        numerical_status = "FAIL";

    end

    timing_status = "PASS";

    if mean_ms > target_ms
        timing_status = "FAIL";
    end

    results(d, :) = [
        n, ...
        nnz(A), ...
        construction_ms, ...
        mean_ms, ...
        median_ms, ...
        min_ms, ...
        max_ms, ...
        max_absolute_error, ...
        norm_error, ...
        target_ms
    ];

    fprintf(
        "  NNZ: %d\n",
        nnz(A)
    );

    fprintf(
        "  Construction: %.6f ms\n",
        construction_ms
    );

    fprintf(
        "  Mean: %.6f ms\n",
        mean_ms
    );

    fprintf(
        "  Median: %.6f ms\n",
        median_ms
    );

    fprintf(
        "  Maximum error: %.3e\n",
        max_absolute_error
    );

    fprintf(
        "  Norm error: %.3e\n",
        norm_error
    );

    fprintf(
        "  Numerical status: %s\n",
        numerical_status
    );

    fprintf(
        "  Timing status: %s\n\n",
        timing_status
    );

end

T = table( ...
    results(:,1), ...
    results(:,2), ...
    results(:,3), ...
    results(:,4), ...
    results(:,5), ...
    results(:,6), ...
    results(:,7), ...
    results(:,8), ...
    results(:,9), ...
    results(:,10), ...
    'VariableNames', { ...
        'dimension', ...
        'nnz', ...
        'construction_ms', ...
        'mean_ms', ...
        'median_ms', ...
        'min_ms', ...
        'max_ms', ...
        'max_absolute_error', ...
        'norm_error', ...
        'target_ms' ...
    } ...
);

writetable(
    T,
    output_file
);

fprintf(
    "Results saved to:\n%s\n",
    output_file
);