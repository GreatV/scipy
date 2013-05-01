"""Test functions for the sparse.linalg.condest module
"""

from __future__ import division, print_function, absolute_import

import numpy as np
from numpy.testing import (assert_allclose, assert_equal, assert_,
        decorators, TestCase, run_module_suite)
import scipy.linalg
import scipy.sparse.linalg
from scipy.sparse.linalg._condest import _condest_core


class MatrixProductOperator(scipy.sparse.linalg.LinearOperator):
    """
    This is purely for condest testing.
    """

    def __init__(self, A, B):
        if A.ndim != 2 or B.ndim != 2:
            raise ValueError('expected ndarrays representing matrices')
        if A.shape[1] != B.shape[0]:
            raise ValueError('incompatible shapes')
        self.A = A
        self.B = B
        self.ndim = 2
        self.shape = (A.shape[0], B.shape[1])

    def matvec(self, x):
        return np.dot(self.A, np.dot(self.B, x))

    def rmatvec(self, x):
        return np.dot(np.dot(x, self.A), self.B)

    def matmat(self, X):
        return np.dot(self.A, np.dot(self.B, X))

    @property
    def T(self):
        return MatrixProductOperator(self.B.T, self.A.T)


class TestCondest(TestCase):

    @decorators.slow
    @decorators.skipif(True, 'this test is annoyingly slow')
    def test_condest_table_3_t_2(self):
        # This will take multiple seconds if your computer is slow like mine.
        # It is stochastic, so the tolerance could be too strict.
        t = 2
        n = 100
        itmax = 5
        nsamples = 5000
        observed = []
        expected = []
        nmult_list = []
        nresample_list = []
        for i in range(nsamples):
            A = scipy.linalg.inv(np.random.randn(n, n))
            est, v, w, nmults, nresamples = _condest_core(A, A.T, t, itmax)
            observed.append(est)
            expected.append(scipy.linalg.norm(A, 1))
            nmult_list.append(nmults)
            nresample_list.append(nresamples)
        observed = np.array(observed, dtype=float)
        expected = np.array(expected, dtype=float)
        relative_errors = np.abs(observed - expected) / expected

        # check the mean underestimation ratio
        underestimation_ratio = observed / expected
        assert_(0.99 < np.mean(underestimation_ratio) < 1.0)

        # check the max and mean required column resamples
        assert_equal(np.max(nresample_list), 2)
        assert_(0.05 < np.mean(nresample_list) < 0.2)

        # check the proportion of norms computed exactly correctly
        nexact = np.count_nonzero(relative_errors < 1e-14)
        proportion_exact = nexact / float(nsamples)
        assert_(0.9 < proportion_exact < 0.95)

        # check the average number of matrix*vector multiplications
        assert_(3.5 < np.mean(nmult_list) < 4.5)


    def test_condest_table_5_t_1(self):
        # "note that there is no randomness and hence only one estimate for t=1"
        t = 1
        n = 100
        itmax = 5
        alpha = 1 - 1e-6
        A = -scipy.linalg.inv(np.identity(n) + alpha*np.eye(n, k=1))
        first_col = np.array([1] + [0]*(n-1))
        first_row = np.array([(-alpha)**i for i in range(n)])
        B = -scipy.linalg.toeplitz(first_col, first_row)
        assert_allclose(A, B)
        est, v, w, nmults, nresamples = _condest_core(B, B.T, t, itmax)
        exact_value = scipy.linalg.norm(B, 1)
        underest_ratio = est / exact_value
        assert_allclose(underest_ratio, 0.05, rtol=1e-4)
        assert_equal(nmults, 11)
        assert_equal(nresamples, 0)
        # check the non-underscored version of condest
        est_plain = scipy.sparse.linalg.condest(B, t=t, itmax=itmax)
        assert_allclose(est, est_plain)


    def _help_product_norm_slow(self, A, B):
        # for profiling
        C = np.dot(A, B)
        return scipy.linalg.norm(C, 1)

    def _help_product_norm_fast(self, A, B):
        # for profiling
        t = 2
        itmax = 5
        D = MatrixProductOperator(A, B)
        est, v, w, nmults, nresamples = _condest_core(D, D.T, t, itmax)
        return est

    @decorators.slow
    def test_condest_linear_operator(self):
        # Define a matrix through its product A B.
        # Depending on the shapes of A and B,
        # it could be easy to multiply this product by a small matrix,
        # but it could be annoying to look at all of
        # the entries of the product explicitly.
        n = 6000
        k = 3
        A = np.random.randn(n, k)
        B = np.random.randn(k, n)
        fast_estimate = self._help_product_norm_fast(A, B)
        exact_value = self._help_product_norm_slow(A, B)
        self.assert_(fast_estimate < exact_value < 3*fast_estimate)


if __name__ == '__main__':
    run_module_suite()

