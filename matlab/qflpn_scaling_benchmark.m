function qflpn_scaling_benchmark()

    clc;

    % ============================================================
    % QFLPN DETERMINISTIC CSR/SPARSE SCALING BENCHMARK
    %
    % State-space dimensions:
    %
    %       N = 1,024
    %       N = 10,000
    %       N = 100,000
    %
    % IMPORTANT:
    % These are state-space dimensions, NOT qubit counts.
    %
    % N = 1,024 = 2^10 -> equivalent to 10 qubits.
    % N = 10,000 and N = 100,000 are general numerical
    % state-space dimensions.
    %
    % No random numbers.
    % No Monte Carlo.
    % No dense N x N matrix.
    %
    % Operator:
    %
    %     U = blockdiag(R(theta), R(theta), ...)
    %
    % where:
    %
    %     R(theta) =
    %
    %       [ cos(theta)  -sin(theta) ]
    %       [ sin(theta)   cos(theta) ]
    %
    % and:
    %
    %     theta = 2 asin(sqrt(mu))
    %
    %     mu = 0.70
    %
    % Numerical validation is performed against an
    % independent analytical reference.
    %
    % ============================================================


    % ------------------------------------------------------------
    % Experimental parameters
    % ------------------------------------------------------------

    dimensions = [
        1024, ...
        10000, ...
        100000
    ];

    mu = 0.70;

    warmup_repetitions = 20;

    benchmark_repetitions = 1000;

    target_ms = 15.0;

    numerical_tolerance = 1.0e-12;


    % ------------------------------------------------------------
    % Output directory
    % ------------------------------------------------------------

    output_directory = ...
        'results';

    if exist(
        output_directory, ...
        'dir'
    ) ~= 7

        mkdir(
            output_directory
        );

    end


    output_file = fullfile(
        output_directory, ...
        'qflpn_scaling_matlab.csv'
    );


    % ------------------------------------------------------------
    % Open CSV
    % ------------------------------------------------------------

    fid = fopen(
        output_file, ...
        'w'
    );

    if fid == -1

        error(
            'Cannot open output file: %s', ...
            output_file
        );

    end


    fprintf(
        fid, ...
        ['language,dimension_type,states,' ...
         'equivalent_qubits,nnz,mu,warmup,' ...
         'repetitions,construction_ms,mean_ms,' ...
         'median_ms,min_ms,max_ms,' ...
         'maximum_error,input_norm,output_norm,' ...
         'norm_error,target_ms,numerical_tolerance,' ...
         'numerical_status,timing_status,' ...
         'matlab_version,computer\\n']
    );


    % ------------------------------------------------------------
    % Experimental information
    % ------------------------------------------------------------

    fprintf(
        '============================================================\n'
    );

    fprintf(
        'QFLPN DETERMINISTIC SPARSE SCALING BENCHMARK\n'
    );

    fprintf(
        '============================================================\n'
    );

    fprintf(
        'Dimensions: 1024, 10000, 100000\n'
    );

    fprintf(
        'mu = %.12f\n', ...
        mu
    );

    fprintf(
        'Warm-up repetitions = %d\n', ...
        warmup_repetitions
    );

    fprintf(
        'Benchmark repetitions = %d\n', ...
        benchmark_repetitions
    );

    fprintf(
        'Target = %.3f ms\n', ...
        target_ms
    );

    fprintf(
        'Monte Carlo = NOT USED\n\n'
    );


    % ------------------------------------------------------------
    % Operator coefficients
    % ------------------------------------------------------------

    theta = ...
        2.0 * asin(
            sqrt(mu)
        );

    c = cos(theta);

    s = sin(theta);


    % ------------------------------------------------------------
    % Main benchmark
    % ------------------------------------------------------------

    for dimension_index = ...
            1:length(dimensions)

        states = ...
            dimensions(
                dimension_index
            );


        % --------------------------------------------------------
        % Validate dimension
        % --------------------------------------------------------

        if mod(
            states, ...
            2
        ) ~= 0

            fclose(fid);

            error(
                'State-space dimension must be even.'
            );

        end


        fprintf(
            'Running N = %d\n', ...
            states
        );


        % --------------------------------------------------------
        % Equivalent qubits
        % --------------------------------------------------------

        q = log2(
            states
        );

        if abs(
            q - round(q)
        ) < 1.0e-12

            equivalent_qubits = ...
                round(q);

            equivalent_qubits_csv = ...
                sprintf(
                    '%d', ...
                    equivalent_qubits
                );

        else

            equivalent_qubits = [];
            equivalent_qubits_csv = '';

        end


        % --------------------------------------------------------
        % Deterministic initial state
        % --------------------------------------------------------

        index = ...
            (0:(states - 1))';

        x = ...
            sin(index) ...
            + ...
            0.5 .* ...
            cos(0.37 .* index);

        input_norm = ...
            norm(
                x, ...
                2
            );

        if input_norm == 0

            fclose(fid);

            error(
                'Initial state has zero norm.'
            );

        end

        x = ...
            x ./ input_norm;


        % --------------------------------------------------------
        % Sparse matrix construction
        % --------------------------------------------------------

        number_of_blocks = ...
            states / 2;

        block_index = ...
            (0:(number_of_blocks - 1))';

        first = ...
            2 .* block_index + 1;

        second = ...
            first + 1;


        % Four non-zero entries per 2x2 block:
        %
        % [ c  -s ]
        % [ s   c ]

        rows = [
            first;
            first;
            second;
            second
        ];

        cols = [
            first;
            second;
            first;
            second
        ];

        values = [
            c .* ones(
                number_of_blocks, ...
                1
            );

            -s .* ones(
                number_of_blocks, ...
                1
            );

            s .* ones(
                number_of_blocks, ...
                1
            );

            c .* ones(
                number_of_blocks, ...
                1
            )
        ];


        % --------------------------------------------------------
        % Construction timing
        % --------------------------------------------------------

        construction_start = tic;

        A = sparse(
            rows, ...
            cols, ...
            values, ...
            states, ...
            states
        );

        construction_ms = ...
            toc(
                construction_start
            ) * 1000.0;


        % --------------------------------------------------------
        % Structural validation
        % --------------------------------------------------------

        expected_nnz = ...
            2 * states;

        actual_nnz = ...
            nnz(A);

        if actual_nnz ~= expected_nnz

            fclose(fid);

            error(
                ['CSR/sparse structural validation failed: ' ...
                 'expected NNZ=%d, obtained NNZ=%d.'], ...
                expected_nnz, ...
                actual_nnz
            );

        end


        % --------------------------------------------------------
        % Independent analytical reference
        % --------------------------------------------------------

        y_reference = ...
            zeros(
                states, ...
                1
            );


        for k = ...
                1:number_of_blocks

            i = ...
                2 * k - 1;

            j = ...
                2 * k;

            y_reference(i) = ...
                c * x(i) ...
                - ...
                s * x(j);

            y_reference(j) = ...
                s * x(i) ...
                + ...
                c * x(j);

        end


        % --------------------------------------------------------
        % Warm-up
        % --------------------------------------------------------

        y = ...
            zeros(
                states, ...
                1
            );


        for repetition = ...
                1:warmup_repetitions

            y = ...
                A * x;

        end


        % --------------------------------------------------------
        % Timed sparse matrix-vector multiplication
        % --------------------------------------------------------

        times_ms = ...
            zeros(
                benchmark_repetitions, ...
                1
            );


        for repetition = ...
                1:benchmark_repetitions

            start_time = tic;

            y = ...
                A * x;

            times_ms(repetition) = ...
                toc(
                    start_time
                ) * 1000.0;

        end


        % --------------------------------------------------------
        % Numerical validation
        % --------------------------------------------------------

        maximum_error = ...
            max(
                abs(
                    y -
                    y_reference
                )
            );


        output_norm = ...
            norm(
                y, ...
                2
            );


        norm_error = ...
            abs(
                output_norm ...
                - ...
                input_norm
            );


        if ...
            maximum_error <= ...
            numerical_tolerance ...
            && ...
            norm_error <= ...
            numerical_tolerance

            numerical_status = ...
                'PASS';

        else

            numerical_status = ...
                'FAIL';

        end


        % --------------------------------------------------------
        % Timing statistics
        % --------------------------------------------------------

        mean_ms = ...
            mean(
                times_ms
            );


        sorted_times = ...
            sort(
                times_ms
            );


        if mod(
            benchmark_repetitions, ...
            2
        ) == 0

            left = ...
                benchmark_repetitions / 2;

            right = ...
                left + 1;

            median_ms = ...
                (
                    sorted_times(left) ...
                    + ...
                    sorted_times(right)
                ) / 2.0;

        else

            middle = ...
                (
                    benchmark_repetitions + 1
                ) / 2;

            median_ms = ...
                sorted_times(middle);

        end


        min_ms = ...
            min(
                times_ms
            );


        max_ms = ...
            max(
                times_ms
            );


        if mean_ms <= target_ms

            timing_status = ...
                'PASS';

        else

            timing_status = ...
                'FAIL';

        end


        % --------------------------------------------------------
        % Console output
        % --------------------------------------------------------

        fprintf(
            '  NNZ             = %d\n', ...
            actual_nnz
        );

        fprintf(
            '  Construction    = %.6f ms\n', ...
            construction_ms
        );

        fprintf(
            '  Mean SpMV       = %.6f ms\n', ...
            mean_ms
        );

        fprintf(
            '  Median SpMV     = %.6f ms\n', ...
            median_ms
        );

        fprintf(
            '  Minimum SpMV    = %.6f ms\n', ...
            min_ms
        );

        fprintf(
            '  Maximum SpMV    = %.6f ms\n', ...
            max_ms
        );

        fprintf(
            '  Maximum error   = %.3e\n', ...
            maximum_error
        );

        fprintf(
            '  Norm error      = %.3e\n', ...
            norm_error
        );

        fprintf(
            '  Numerical       = %s\n', ...
            numerical_status
        );

        fprintf(
            '  Timing          = %s\n\n', ...
            timing_status
        );


        % --------------------------------------------------------
        % CSV output
        % --------------------------------------------------------

        fprintf(
            fid, ...
            ['MATLAB-compatible,state_space,%d,%s,%d,' ...
             '%.12f,%d,%d,%.12f,%.12f,%.12f,' ...
             '%.12f,%.12f,%.12e,%.12e,%.12e,' ...
             '%.12e,%.12f,%.12e,%s,%s,"%s","%s"\\n'], ...
            states, ...
            equivalent_qubits_csv, ...
            actual_nnz, ...
            mu, ...
            warmup_repetitions, ...
            benchmark_repetitions, ...
            construction_ms, ...
            mean_ms, ...
            median_ms, ...
            min_ms, ...
            max_ms, ...
            maximum_error, ...
            input_norm, ...
            output_norm, ...
            norm_error, ...
            target_ms, ...
            numerical_tolerance, ...
            numerical_status, ...
            timing_status, ...
            version, ...
            computer
        );

    end


    % ------------------------------------------------------------
    % Close CSV
    % ------------------------------------------------------------

    fclose(fid);


    fprintf(
        '============================================================\n'
    );

    fprintf(
        'Benchmark completed.\n'
    );

    fprintf(
        'Results saved to:\n%s\n', ...
        output_file
    );

    fprintf(
        '============================================================\n'
    );

end