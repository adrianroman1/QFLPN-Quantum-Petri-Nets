function qflpn_scaling_benchmark()
% QFLPN_SCALING_BENCHMARK
%
% Deterministic MATLAB scaling benchmark for QFLPN.
%
% Tested state-vector dimensions:
%
%     1024
%     10000
%     100000
%
% Interpretation:
%
%     1024 = 2^10
%
% Therefore 1024 corresponds exactly to a 10-qubit
% state space.
%
% 10000 and 100000 are numerical state-vector dimensions
% and are NOT interpreted as exact 2^n qubit spaces.
%
% The transition operator is sparse and unitary.
%
% Declared QFLPN fuzzy-to-quantum mapping:
%
%     theta(mu) = 2*asin(sqrt(mu))
%
% No Monte Carlo.
% No random sampling.
%
% Output:
%
%     results/scaling/qflpn_matlab_scaling_results.csv


clc;


% ============================================================
% Configuration
% ============================================================

dimensions = [
    1024
    10000
    100000
];

mu = 0.70;

repetitions = 1000;

warmup = 20;

targetMs = 15.0;

tolerance = 1e-12;

outputFile = ...
    fullfile( ...
        'results', ...
        'scaling', ...
        'qflpn_matlab_scaling_results.csv');


% ============================================================
% Header
% ============================================================

fprintf('\n');
fprintf('================================================================\n');
fprintf('QFLPN SCALING BENCHMARK - MATLAB\n');
fprintf('================================================================\n');

fprintf('\n');
fprintf('Deterministic sparse unitary transition.\n');
fprintf('Monte Carlo: NOT USED.\n');
fprintf('Target: %.1f ms\n', targetMs);


% ============================================================
% Prepare output directory
% ============================================================

outputDirectory = ...
    fileparts(outputFile);

if ~exist(outputDirectory, 'dir')

    mkdir(outputDirectory);

end


% ============================================================
% Fuzzy -> quantum angle
% ============================================================

if mu < 0 || mu > 1

    error( ...
        'Fuzzy membership must belong to [0,1].');

end

theta = ...
    2 * asin(sqrt(mu));


% ============================================================
% Rotation coefficients
% ============================================================

c = cos(theta / 2);

s = sin(theta / 2);


% ============================================================
% Open CSV
% ============================================================

fid = fopen( ...
    outputFile, ...
    'w');

if fid == -1

    error( ...
        'Unable to create MATLAB scaling CSV.');

end


fprintf( ...
    fid, ...
    ['language,dimension,qubits_if_power_of_two,' ...
     'nnz,repetitions,warmup,' ...
     'mean_ms,median_ms,min_ms,max_ms,' ...
     'target_ms,norm_error,maximum_error,' ...
     'numerical_status,timing_status\n']);


% ============================================================
% Each state dimension
% ============================================================

for d = 1:length(dimensions)

    dimension = dimensions(d);

    fprintf('\n');
    fprintf( ...
        'Dimension: %d\n', ...
        dimension);


    % --------------------------------------------------------
    % Sparse unitary operator
    % --------------------------------------------------------

    numberOfBlocks = ...
        floor(dimension / 2);

    nnzOperator = ...
        4 * numberOfBlocks;

    if mod(dimension, 2) == 1

        nnzOperator = ...
            nnzOperator + 1;

    end


    rows = zeros(
        nnzOperator,
        1);

    columns = zeros(
        nnzOperator,
        1);

    values = zeros(
        nnzOperator,
        1);


    position = 1;


    for i = 1:2:(dimension - 1)

        rows(position) = i;
        columns(position) = i;
        values(position) = c;

        position = position + 1;


        rows(position) = i;
        columns(position) = i + 1;
        values(position) = -s;

        position = position + 1;


        rows(position) = i + 1;
        columns(position) = i;
        values(position) = s;

        position = position + 1;


        rows(position) = i + 1;
        columns(position) = i + 1;
        values(position) = c;

        position = position + 1;

    end


    if mod(dimension, 2) == 1

        rows(position) = dimension;
        columns(position) = dimension;
        values(position) = 1.0;

    end


    U = sparse( ...
        rows, ...
        columns, ...
        values, ...
        dimension, ...
        dimension);


    % --------------------------------------------------------
    % Deterministic normalized state
    % --------------------------------------------------------

    indices = ...
        (1:dimension).';

    psi = ...
        1 ./ sqrt(double(indices));

    psi = ...
        psi / norm(psi);


    % --------------------------------------------------------
    % Warm-up
    % --------------------------------------------------------

    for k = 1:warmup

        U * psi;

    end


    % --------------------------------------------------------
    % Timed benchmark
    % --------------------------------------------------------

    timings = ...
        zeros(repetitions, 1);

    output = [];


    for k = 1:repetitions

        timer = tic;

        output = U * psi;

        timings(k) = ...
            toc(timer) * 1000.0;

    end


    % --------------------------------------------------------
    % Timing statistics
    % --------------------------------------------------------

    meanMs = ...
        mean(timings);

    medianMs = ...
        median(timings);

    minMs = ...
        min(timings);

    maxMs = ...
        max(timings);


    % --------------------------------------------------------
    % Numerical validation
    % --------------------------------------------------------

    inputNorm = ...
        norm(psi);

    outputNorm = ...
        norm(output);

    normError = ...
        abs(outputNorm - inputNorm);


    reference = ...
        U * psi;

    maximumError = ...
        max(abs(output - reference));


    numericalError = ...
        max( ...
            normError, ...
            maximumError);


    if numericalError <= tolerance

        numericalStatus = ...
            'PASS';

    else

        numericalStatus = ...
            'REVIEW REQUIRED';

    end


    % --------------------------------------------------------
    % Timing status
    % --------------------------------------------------------

    if meanMs <= targetMs

        timingStatus = ...
            'PASS';

    else

        timingStatus = ...
            'TARGET NOT MET';

    end


    % --------------------------------------------------------
    % Qubit interpretation
    % --------------------------------------------------------

    if dimension > 0 && ...
            bitand( ...
                dimension, ...
                dimension - 1) == 0

        qubits = ...
            round(log2(dimension));

        qubitText = ...
            sprintf('%d', qubits);

    else

        qubitText = ...
            'NA';

    end


    % --------------------------------------------------------
    % Console
    % --------------------------------------------------------

    fprintf( ...
        '  NNZ               : %d\n', ...
        nnzOperator);

    fprintf( ...
        '  mean              : %.6f ms\n', ...
        meanMs);

    fprintf( ...
        '  median            : %.6f ms\n', ...
        medianMs);

    fprintf( ...
        '  min               : %.6f ms\n', ...
        minMs);

    fprintf( ...
        '  max               : %.6f ms\n', ...
        maxMs);

    fprintf( ...
        '  norm error        : %.3e\n', ...
        normError);

    fprintf( ...
        '  maximum error     : %.3e\n', ...
        maximumError);

    fprintf( ...
        '  numerical status  : %s\n', ...
        numericalStatus);

    fprintf( ...
        '  15 ms status      : %s\n', ...
        timingStatus);


    % --------------------------------------------------------
    % CSV
    % --------------------------------------------------------

    fprintf( ...
        fid, ...
        ['MATLAB,%d,%s,%d,%d,%d,' ...
         '%.12f,%.12f,%.12f,%.12f,' ...
         '%.6f,%.12e,%.12e,%s,%s\n'], ...
        dimension, ...
        qubitText, ...
        nnzOperator, ...
        repetitions, ...
        warmup, ...
        meanMs, ...
        medianMs, ...
        minMs, ...
        maxMs, ...
        targetMs, ...
        normError, ...
        maximumError, ...
        numericalStatus, ...
        timingStatus);

end


% ============================================================
% Close CSV
% ============================================================

fclose(fid);


fprintf('\n');
fprintf( ...
    'CSV exported:\n  %s\n', ...
    outputFile);

fprintf('\n');
fprintf( ...
    'QFLPN MATLAB scaling benchmark completed.\n');


end
