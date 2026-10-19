"""Exact sufficient-statistic compression of repeated transport signatures."""

import numpy as np
from scipy.linalg import cho_solve


def grouped_design(chol, signature_index, residual, signatures):
    """Evaluate g'C^-1g and g'C^-1y without expanding repeated rows.

    g = B signatures, where B has one 1 per observation. Covariance remains the
    original full matrix: repeated readings never become independent, get
    averaged, or lose instrument/background/time correlations.
    """
    count = len(signatures)
    basis = np.eye(count)[signature_index]
    inverse_basis = cho_solve((chol, True), basis, check_finite=False)
    information = basis.T @ inverse_basis
    information = (information + information.T) / 2
    white = np.linalg.cholesky(information).T @ signatures
    norm = np.sum(white**2, axis=0)
    dot = signatures.T @ (inverse_basis.T @ residual)
    return norm, dot, inverse_basis
