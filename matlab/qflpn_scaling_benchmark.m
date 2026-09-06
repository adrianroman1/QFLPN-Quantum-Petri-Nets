
function qflpn_scaling_benchmark()

    clc;

    dimensions = [1024, 10000, 100000];

    warmup_repetitions = 20;
    benchmark_repetitions = 1000;

    target_ms = 15.0;

    mu = 0.70;

    theta = 2.0 * asin(sqrt(mu));

    c = cos(theta);
    s = sin(theta);

    fprintf('QFLPN deterministic sparse scaling benchmark\n');
    fprintf('mu = %.12f\n', mu);
    fprintf('theta = %.12f rad\n', theta);
    fprintf('Warmup repetitions = %d\n', warmup_repetitions);
    fprintf('Benchmark repetitions = %d\n', benchmark_repetitions);
    fprintf('Target = %.3f ms\n\n', target_ms);

    output_directory = 'results';

    if exist(output_directory, 'dir') ~= 7
        mkdir(output_directory);
    end

    output_file = fullfile( ...
        output_directory, ...
        'qflpn_scaling_matlab.csv');

    fid = fopen(output_file, 'w');

    if fid == -1
        error('Cannot open output file: %s', output_file);
    end

    fprintf(fid, ...
        ['language,dimension,nnz,warmup,repetitions,' ...
         'construction_ms,mean_ms,median_ms,min_ms,max_ms,' ...
         'maximum_error,norm_error,numerical_status,timing_status\n']);

    for d = 1:length(dimensions)

        N = dimensions(d);

        fprintf('Running N=%d\n', N);

        index = (0:(N - 1))';

        x = sin(index) + 0.5 .* cos(0.37 .* index);

        x_norm = norm(x, 2);

        if x_norm == 0
            fclose(fid);
            error('Input vector has zero norm for N=%d.', N);
        end

        x = x ./ x_norm;

        number_of_blocks = floor(N / 2);

        rows = zeros(4 * number_of_blocks, 1);
        cols = zeros(4 * number_of_blocks, 1);
        values = zeros(4 * number_of_blocks, 1);

        position = 1;

        for k = 1:number_of_blocks

            i = 2 * k - 1;
            j = 2 * k;

            rows(position) = i;
            cols(position) = i;
            values(position) = c;
            position = position + 1;

            rows(position) = i;
            cols(position) = j;
            values(position) = -s;
            position = position + 1;

            rows(position) = j;
            cols(position) = i;
            values(position) = s;
            position = position + 1;

            rows(position) = j;
            cols(position) = j;
            values(position) = c;
            position = position + 1;

        end

        if mod(N, 2) == 1

            rows(position) = N;
            cols(position) = N;
            values(position) = 1.0;

            position = position + 1;

        end

        rows = rows(1:(position - 1));
        cols = cols(1:(position - 1));
        values = values(1:(position - 1));

        construction_start = tic;

        A = sparse(rows, cols, values, N, N);

        construction_ms = toc(construction_start) * 1000.0;

        nnz_value = nnz(A);

        fprintf('  NNZ: %d\n', nnz_value);
        fprintf('  Construction: %.6f ms\n', construction_ms);

        y_reference = zeros(N, 1);

        for k = 1:number_of_blocks

            i = 2 * k - 1;
            j = 2 * k;

            y_reference(i) = ...
                c * x(i) - s * x(j);

            y_reference(j) = ...
                s * x(i) + c * x(j);

        end

        if mod(N, 2) == 1
            y_reference(N) = x(N);
        end

        y = zeros(N, 1);

        for r = 1:warmup_repetitions
            y = A * x;
        end

        times_ms = zeros(benchmark_repetitions, 1);

        for r = 1:benchmark_repetitions

            start_time = tic;

            y = A * x;

            elapsed_ms = toc(start_time) * 1000.0;

            times_ms(r) = elapsed_ms;

        end

        maximum_error = max(abs(y - y_reference));

        norm_error = abs(norm(y, 2) - norm(x, 2));

        numerical_tolerance = 1.0e-12;

        numerical_status = 'FAIL';

        if maximum_error <= numerical_tolerance && ...
           norm_error <= numerical_tolerance

            numerical_status = 'PASS';

        end

        mean_ms = mean(times_ms);

        sorted_times = sort(times_ms);

        if mod(benchmark_repetitions, 2) == 0

            middle_left = benchmark_repetitions / 2;
            middle_right = middle_left + 1;

            median_ms = ...
                (sorted_times(middle_left) + ...
                 sorted_times(middle_right)) / 2.0;

        else

            middle = ...
                (benchmark_repetitions + 1) / 2;

            median_ms = sorted_times(middle);

        end

        min_ms = min(times_ms);
        max_ms = max(times_ms);

        timing_status = 'FAIL';

        if mean_ms <= target_ms
            timing_status = 'PASS';
        end

        fprintf('  Mean: %.6f ms\n', mean_ms);
        fprintf('  Median: %.6f ms\n', median_ms);
        fprintf('  Minimum: %.6f ms\n', min_ms);
        fprintf('  Maximum: %.6f ms\n', max_ms);
        fprintf('  Maximum error: %.3e\n', maximum_error);
        fprintf('  Norm error: %.3e\n', norm_error);
        fprintf('  Numerical status: %s\n', numerical_status);
        fprintf('  Timing status: %s\n\n', timing_status);

        fprintf(fid, ...
            ['MATLAB,%d,%d,%d,%d,%.12f,%.12f,%.12f,' ...
             '%.12f,%.12f,%.12e,%.12e,%s,%s\n'], ...
            N, ...
            nnz_value, ...
            warmup_repetitions, ...
            benchmark_repetitions, ...
            construction_ms, ...
            mean_ms, ...
            median_ms, ...
            min_ms, ...
            max_ms, ...
            maximum_error, ...
            norm_error, ...
            numerical_status, ...
            timing_status);

    end

    fclose(fid);

    fprintf('Benchmark completed successfully.\n');
    fprintf('Results written to:\n');
    fprintf('%s\n', output_file);

end