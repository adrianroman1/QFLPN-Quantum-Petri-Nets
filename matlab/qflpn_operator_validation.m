clear;
clc;

dimensions = [1024, 10000, 100000];

mu = 0.70;
warmup = 20;
repetitions = 1000;
target_ms = 15.0;

output_dir = "results";

if ~exist(output_dir, "dir")
    mkdir(output_dir);
end

output_file = fullfile(
    output_dir,
    "qflpn_operator_validation_matlab.csv"
);

results = [];

theta = 2 * asin(sqrt(mu));
c = cos(theta);
s = sin(theta);

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

    construction_ms = toc(construction_start) * 1000;

    idx = (0:n-1)';

    x = sin(idx) + ...
        0.5 * cos(0.37 * idx);

    x = x / norm(x);

    y_reference = zeros(n, 1);

    y_reference(1:2:end) = ...
        c * x(1:2:end) - ...
        s * x(2:2:end);

    y_reference(2:2:end) = ...
        s * x(1:2:end) + ...
        c * x(2:2:end);

    y_sparse = A * x;

    max_absolute_error = ...
        max(abs(y_sparse - y_reference));

    norm_error = ...
        abs(norm(y_sparse) - norm(x));

    for k = 1:warmup
        y = A * x;
    end

    times_ms = zeros(repetitions, 1);

    for k = 1:repetitions

        t = tic;
        y = A * x;
        times_ms(k) = toc(t) * 1000;

    end

    mean_ms = mean(times_ms);
    median_ms = median(times_ms);
    min_ms = min(times_ms);
    max_ms = max(times_ms);

    numerical_status = "PASS";

    if max_absolute_error > 1e-12 || ...
       norm_error > 1e-12
        numerical_status = "FAIL";
    end

    timing_status = "PASS";

    if mean_ms > target_ms
        timing_status = "FAIL";
    end

    result = [
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

    results = [
        results;
        result
    ];

    fprintf(
        "  mean = %.6f ms\n",
        mean_ms
    );

    fprintf(
        "  max error = %.3e\n",
        max_absolute_error
    );

    fprintf(
        "  norm error = %.3e\n",
        norm_error
    );

    fprintf("\n");

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

writetable(T, output_file);

fprintf(
    "Saved: %s\n",
    output_file
);
