function [psi, rho, theta] = qflpn_quantum_core(mu, verbose)
% QFLPN_QUANTUM_CORE
%
% Core 4-qubit QFLPN reference model.
%
% Declared fuzzy-to-quantum mapping:
%
%     theta(mu) = 2*asin(sqrt(mu))
%
% and therefore:
%
%     RY(theta(mu))*|0>
%
% gives:
%
%     P(|1>) = mu.
%
% The four-qubit state is constructed using
% the tensor product of the individual qubit states.
%
% Inputs:
%   mu      - four fuzzy memberships in [0,1]
%   verbose - optional logical flag controlling console output
%
% Outputs:
%   psi     - 16x1 state vector
%   rho     - 16x16 density matrix
%   theta   - four RY rotation angles
%
% No Monte Carlo.

    % --------------------------------------------------------
    % Default display mode
    % --------------------------------------------------------

    if nargin < 2
        verbose = true;
    end

    % --------------------------------------------------------
    % Input validation
    % --------------------------------------------------------

    mu = double(mu(:).');

    if numel(mu) ~= 4
        error( ...
            'QFLPN reference model requires exactly 4 memberships.');
    end

    if any(mu < 0) || any(mu > 1)
        error( ...
            'Fuzzy memberships must belong to [0,1].');
    end

    % --------------------------------------------------------
    % Fuzzy -> quantum mapping
    % --------------------------------------------------------

    theta = 2 .* asin(sqrt(mu));

    % --------------------------------------------------------
    % Individual qubit states
    % --------------------------------------------------------

    states = cell(1,4);

    for k = 1:4

        c = cos(theta(k)/2);
        s = sin(theta(k)/2);

        states{k} = [c; s];

    end

    % --------------------------------------------------------
    % Tensor-product state
    % --------------------------------------------------------

    psi = states{1};

    for k = 2:4
        psi = kron(psi, states{k});
    end

    % --------------------------------------------------------
    % Normalization
    % --------------------------------------------------------

    normalization_error = abs(norm(psi) - 1.0);

    if normalization_error > 1e-12
        error( ...
            'State normalization failed: %.3e', ...
            normalization_error);
    end

    % --------------------------------------------------------
    % Density matrix
    % --------------------------------------------------------

    rho = psi * psi';

    % --------------------------------------------------------
    % Optional display
    %
    % IMPORTANT:
    % Benchmark mode uses verbose=false so console I/O does
    % not contaminate the measured execution time.
    % --------------------------------------------------------

    if verbose

        fprintf('\n');
        fprintf('============================================\n');
        fprintf('QFLPN QUANTUM CORE - MATLAB\n');
        fprintf('============================================\n');

        fprintf('\nFuzzy memberships:\n');

        for k = 1:4
            fprintf( ...
                'mu(%d) = %.6f\n', ...
                k, ...
                mu(k));
        end

        fprintf('\nRY angles:\n');

        for k = 1:4
            fprintf( ...
                'theta(%d) = %.12f rad\n', ...
                k, ...
                theta(k));
        end

        fprintf('\nState dimension: %d\n', length(psi));

        fprintf( ...
            'State norm: %.15f\n', ...
            norm(psi));

        fprintf( ...
            'Probability sum: %.15f\n', ...
            sum(abs(psi).^2));

        fprintf( ...
            'Density matrix: %d x %d\n', ...
            size(rho,1), ...
            size(rho,2));

        fprintf('\nComputational-basis probabilities:\n');

        probabilities = abs(psi).^2;

        for k = 1:length(probabilities)

            if probabilities(k) > 1e-14

                basis = dec2bin(k-1,4);

                fprintf( ...
                    '|%s> : %.12f\n', ...
                    basis, ...
                    probabilities(k));

            end
        end

        fprintf('\nQFLPN quantum core completed.\n');

    end

end