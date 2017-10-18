"""ADMM implementation for PECOK"""

# author: Martin Royer <martin.royer@math.u-psud.fr>
# License: MIT

import numpy as np
from scipy import linalg as la


###############################################################################
def operator_lstarllstarinv(u, v):
    """Operator \widetilde{L}^* on (u,v) in R^{p+1} -> R^{p*p}"""
    return u.repeat(u.size).reshape((u.size, u.size)) + np.diag(np.repeat(v, u.size))

def proj_lin_Hrows(Y, K):
    """Projection onto \Pi_{\mathcal{A}}(Y)"""
    n_samples,_ = Y.shape
    x = np.sum(Y, 1) - 1
    y = np.trace(Y) - K
    invx = (x+(np.sum(x)-y*n_samples)/(n_samples**2-n_samples))/n_samples
    invy = ((y-np.sum(x))/(n_samples-1)+y)/n_samples
    Y = Y - operator_lstarllstarinv(invx, invy)
    return Y

def operator_lstarllstarinv_sym(u, v):
    """Operator \widetildetilde{L}^*_{sym} on (u,v) in R^{p+1} -> R^{p*p}"""
    temp = operator_lstarllstarinv(u, v)
    return (temp + temp.T)-np.diag(np.diag(temp))

def proj_lin_Hsymmetric(Y, K):
    """Projection onto \Pi_{\mathcal{A}sym}(Y)"""
    n_samples,_ = Y.shape
    x = np.sum(Y, 1) - 1
    y = np.trace(Y) - K
    invx = (x-(np.sum(x)+y)/(2*n_samples))/(n_samples-1)
    invy = (y-(np.sum(x)+y)/(2*n_samples))/(n_samples-1)
    Y = Y - operator_lstarllstarinv_sym(invx, invy)
    return Y

# ### - Y-Projection
def proj_positive(x, thresh=0):
    """Project onto component-positive matrix"""
    x[x < thresh] = 0
    return x

# ### - Z-Projection
def proj_Snp_imp(Y):
    """Improved projection onto semi-definite positive matrix"""
    n_samples,_ = Y.shape
    eig_vals = la.eigh(Y, eigvals_only=True)
    n_val_neg = np.sum(eig_vals<0)
    if n_val_neg == 0:
        return Y
    if n_val_neg == n_samples:
        return np.zeros((n_samples,n_samples))
    if n_val_neg < n_samples-n_val_neg:
        eig_vals, v = la.eigh(-Y, eigvals=(n_samples - n_val_neg, n_samples - 1))
        Y = Y + v.dot(np.diag(eig_vals)).dot(v.T)
    else:
        eig_vals, v = la.eigh(Y, eigvals=(n_val_neg, n_samples - 1))
        Y = v.dot(np.diag(eig_vals)).dot(v.T)
    return Y

# ### - Main method
n_max = 3000
def pecok_admm(relational_data, K, n_iter_max=n_max, rho=1.0):
    """Implementation of Alternating Direction Method of Multipliers

    Parameters
    ----------
    relational_data : symmetric matrix of relational data (e.g. gram matrix), shape=(n_samples, n_samples)
        Training instances to cluster."""
    n_samples,_ = relational_data.shape
    relational_data = relational_data / np.linalg.norm(relational_data)

    X,Y,Z = np.identity(n_samples), np.identity(n_samples), np.identity(n_samples)
    U,V,W = np.zeros((n_samples,n_samples)), np.zeros((n_samples,n_samples)), np.zeros((n_samples,n_samples))
    Xbar = (X + Y + Z)/3

    n_iter = 0
    while n_iter < n_iter_max:
        n_iter = n_iter + 1

        oldXbar = Xbar
        X = proj_lin_Hsymmetric(Xbar - U + relational_data / rho, K)
        Y = proj_positive(Xbar - V)
        Z = proj_Snp_imp(Xbar - W)
        Xbar = (X + Y + Z)/3

        U = U + X - Xbar
        V = V + Y - Xbar
        W = W + Z - Xbar

        res_dual = rho * np.linalg.norm(Xbar-oldXbar)
        res_primal = np.linalg.norm((X-Xbar, Z-Xbar, Y-Xbar))
        if not (is_primal_high(res_primal, X, Y, Z) or is_dual_high(res_dual, Y, Z)):
            break
    print("ADMM ends -- n_iter=%i, rho=%2.2f" % (n_iter, rho))
    print("          -- res_primal=%.3e, res_dual=%.3e" % (res_primal, res_dual))
    return Z


# ### - Updates
epsilon = 1e-8
def is_primal_high(res_primal, X, Y, Z):
    return res_primal > epsilon * np.max((np.linalg.norm(X), np.linalg.norm(Y), np.linalg.norm(Z)))

def is_dual_high(res_dual, Y, Z):
    return res_dual > epsilon * (np.sqrt(Y.shape[0]) + np.linalg.norm(Y) + np.linalg.norm(Z))