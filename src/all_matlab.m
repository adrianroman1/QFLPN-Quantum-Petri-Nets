function [eigenValues, isContractive] = analyzeQuantumPetri(K_n)
    % analyzeQuantumPetri Analiza spectrală a matricii K_n (Kronecker rare)
    %   eigenValues = vectorul valorilor proprii
    %   isContractive = boolean (true dacă maxi |lambda| < 1)

    % Convertim la matrice densă doar pentru dimensiuni demonstrative.
    % Pentru dimensiuni mari se folosește algoritmii iterativi (eigs) pe structuri sparse.
    if issparse(K_n)
        % Folosiți eigs pentru matrice sparse mari
        opts.tol = 1e-6;
        try
            eigenValues = eigs(K_n, 6, 'largestabs', opts);
        catch
            % fallback la conversie densă dacă eigs nu este aplicabil
            eigenValues = eig(full(K_n));
        end
    else
        eigenValues = eig(full(K_n));
    end

    maxEigen = max(abs(eigenValues));
    isContractive = (maxEigen < 1);
end
