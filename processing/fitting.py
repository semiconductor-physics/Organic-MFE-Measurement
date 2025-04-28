import numpy as np
from numpy import inf
from numpy.typing import ArrayLike
from typing import Callable
from scipy.optimize import curve_fit
from abc import ABC
from typing import Any

import logging
logger = logging.getLogger(__name__)


def cole(x, B0, alpha, c):
    B = abs(x)
    temp = (B / B0) ** alpha
    temp2 = (B / B0) ** (2*alpha)
    cs = np.cos((np.pi * alpha) / 2)
    return c* ((1 + temp * cs) / (1 + 2 * temp * cs + temp2) - 1)

def double_cole(x, B0_1, B0_2, alpha_1, alpha_2, c):
    B = abs(x)
    temp_1 = (B / B0_1) ** alpha_1
    temp2_1 = (B / B0_1) ** (2*alpha_1)
    cs = np.cos((np.pi * alpha_1) / 2)
    cole_1 = c* ((1 + temp_1 * cs) / (1 + 2 * temp_1 * cs + temp2_1) - 1)
    
    temp_2 = (B / B0_2) ** alpha_2
    temp2_2 = (B / B0_2) ** (2*alpha_2)
    cs = np.cos((np.pi * alpha_2) / 2)
    cole_2 = (1 + temp_2 * cs) / (1 + 2 * temp_2 * cs + temp2_2) - 1
    return cole_1 + cole_2

def cole_lorentzian(x, B0_1, B0_2, alpha, MFE_LF, MFE_HF, d):
    cole_LF = cole(x, B0_1, alpha, MFE_LF)
    lorentzian_HF = lorentzian(x, B0_2, MFE_HF)
    return cole_LF + lorentzian_HF + d *x 

def lorentzian_cole(x, B0_1, B0_2, alpha, MFE_LF, MFE_HF, d):
    cole_HF = cole(x, B0_2, alpha, MFE_HF)
    lorentzian_LF = lorentzian(x, B0_1, MFE_LF)
    return lorentzian_LF + cole_HF + d *x 

def non_lorentzian(x, B0, MFE_max):
    return MFE_max * (x**2/ (np.abs(x) + B0)**2)

def double_non_lorentzian(x, B0_LF, B0_HF, MFE_LF, MFE_HF):
    return non_lorentzian(x, B0_LF, MFE_LF) + non_lorentzian(x, B0_HF, MFE_HF)

def lorentzian(x, B0, MFE_max):
    return MFE_max * (x**2/ (x**2 + B0**2))

def double_lorentzian(x, B0_LF, B0_HF, MFE_LF, MFE_HF):
    return lorentzian(x, B0_LF, MFE_LF) + lorentzian(x, B0_HF, MFE_HF)

def lorentzian_non_lorentzian(x, B0_LF, B0_HF, MFE_LF, MFE_HF):
    return lorentzian(x, B0_LF, MFE_LF) + non_lorentzian(x, B0_HF, MFE_HF)

def soc_risc(x, a, b, c, B1, B2, B3):
    MEL_isc = lorentzian(x, a, B1)
    MEL_risc = lorentzian(x, b, B2)
    MEL_tca = non_lorentzian(x, c, B3)
    return MEL_isc - MEL_risc + MEL_tca

def calc_rmse(predicted_y, true_y)-> float:
    return np.sqrt(np.mean((predicted_y - true_y) ** 2))

def calc_mae(predicted_y, true_y )-> float:
    return np.mean(np.abs(predicted_y - true_y))

def calc_r2(predicted_y, true_y) -> float:
    ss_res = np.sum((true_y - predicted_y) ** 2)
    ss_tot = np.sum((true_y - np.mean(true_y)) ** 2)
    return 1 - (ss_res / ss_tot)

def calc_aic(predicted_y, true_y, n_model_params) -> float:
    rse = np.mean((true_y - predicted_y) ** 2) #    estimator for the rse might need correction term (see An Introduction to Statistical Learning with Applications in Python p.75)
    d = len(true_y)
    return d * np.log(rse) +  2 * n_model_params

def calc_bic(predicted_y, true_y, n_model_params) -> float:
    rse = np.mean((true_y - predicted_y) ** 2) #    estimator for the rse might need correction term (see An Introduction to Statistical Learning with Applications in Python p.75)
    d = len(true_y)
    return d * np.log(rse) +  n_model_params * np.log(d)

def calc_cp(predicted_y, true_y, n_model_params) -> float: #Mallows Cp
    residuals = true_y- predicted_y
    d = len(true_y)
    rss = np.sum(residuals ** 2)
    return (1 / n_model_params) *(rss + 2 * d* (rss / n_model_params))

def calc_adjusted_r2(predicted_y, true_y, n_model_params) -> float:
    rss = np.sum((true_y - predicted_y)**2)
    y_mean = np.mean(true_y)
    tss = np.sum(true_y - y_mean)**2
    d = len(true_y)
    return 1- ((rss/ (n_model_params - d - 1)) / (tss / (n_model_params -1)))


def get_g(tau: np.ndarray, B0, alpha) -> np.ndarray:
    logger.debug(f'Get g with: B0: {B0}, alpha: {alpha}')
    delta_g = 0.002
    µ_B = 9.2740100783e-24
    h_bar = 1.054571817e-34
    tau_0 = (h_bar / (µ_B * delta_g * B0))*10**9 #in µs
    x = np.log(tau/tau_0)
    unnormalized_g = (1 / (2 * np.pi)) * ((np.sin(np.pi * alpha)) / ((np.cosh((alpha * x)) + np.cos(np.pi * alpha))))
    max_value = np.max(unnormalized_g)
    return unnormalized_g / max_value

class DipModel(ABC):
    def __init__(self, f: Callable, name: str=None) -> None:
        self.f = f
        self.name = name
        if name is None:
            self.name = f.__name__
        self.params: list[float] = []
        self.param_names = []
        self.params_err = []
        self.fitted = False

    def __str__(self) -> str:
        return self.name

    def fit(self, x_data, y_data, p0:list[float] = None, bounds:tuple[list, list]=(-np.inf, np.inf)):
        logger.info(f'trying to fit {self.name}')
        try:
            params, cov, info, mesg, _ = curve_fit(f=self.f, xdata=x_data, ydata=y_data, maxfev=500, p0=p0, bounds=bounds, full_output=True)
        except RuntimeError as e:
            logger.error(f'{self.name}: {e}')
            return
        except Exception as e:
            logger.error(e)
            raise e
        self.fitted = True
        self.params = params
        self.params_err = np.sqrt(np.diag(cov))
        return

    def evaluate(self, x_data: ArrayLike, true_y: ArrayLike) -> tuple[float, float, float, float, float, float, float]:
        if not self.fitted:
            raise RuntimeError(f'{self.name} not fitted. Run fit first!')
        true_y = np.array(true_y)
        x_data = np.array(x_data)
        predicted_y = self.predict(x_data)
        r2 = calc_r2(predicted_y, true_y)
        rmse = calc_rmse(predicted_y, true_y)
        mae = calc_mae(predicted_y, true_y)
        adjusted_r2 = calc_adjusted_r2(predicted_y, true_y, len(self.params))
        aic = calc_aic(predicted_y, true_y, len(self.params))
        bic = calc_bic(predicted_y, true_y, len(self.params))
        cp = calc_cp(predicted_y, true_y, len(self.params))
        return r2, rmse, mae, aic, bic, cp, adjusted_r2

    def predict(self, x_data):
        if not self.fitted:
            logger.error(f'{self.name} not fitted. Run fit first!')
            return
        return np.array([self.f(x, * self.params) for x in x_data])
        
    def get_fitted_function(self):
        if not self.fitted:
            logger.error(f'{self.name} not fitted. Run fit first!')
            return
        def f(x):
            return self.f(x, *self.params)
        return f

    def get_g(self, tau: np.ndarray) -> np.ndarray:
        pass
        
class ComposedDipModel(DipModel):
    def __init__(self, f: Callable[..., Any], name: str = None) -> None:
        super().__init__(f, name)
    
    def get_fitted_component_functions(self):
        raise NotImplementedError(f"get components for {self.name} not implemented")

class ColeModel(DipModel):
    def __init__(self, name: str = None) -> None:
        f = cole
        super().__init__(f, name)
        self.param_names = ['B0', 'alpha', 'c']

    def fit(self, x_data, y_data):
        p0: list[float] = [10, 1, 2] 
        bounds = ([0, 0, -40], [inf, 1 , 40])
        return super().fit(x_data, y_data, p0, bounds)
    
    def get_g(self, tau):
        if len(self.params) == 0:
            return
        B0 = self.params[0]
        alpha = self.params[1]
        return get_g(tau, B0, alpha)

class ColeLorentzianModel(ComposedDipModel):
    def __init__(self, name: str = None) -> None:
        f = cole_lorentzian
        super().__init__(f, name)
        self.param_names = ['B0_LF_cole', 'B0_HF_lorentzian', 'alpha', 'MFE_LF_cole', 'MFE_HF_lorentzian', 'd_lin']

    def fit(self, x_data, y_data):
        p0: list[float] = [5, 100, 0.5, 2, -1, 1] 
        bounds = ([0, 4, 0, -30, -30, -inf], [20, inf, 1, 30, 30, inf])
        return super().fit(x_data, y_data, p0, bounds)
    
    def get_g(self, tau):
        if len(self.params) == 0:
            return
        B0 = self.params[0]
        alpha = self.params[2]
        return get_g(tau, B0, alpha)
    
    def get_fitted_component_functions(self):
        if not self.fitted:
            logger.error(f'{self.name} not fitted. Run fit first!')
            return
        components = {}
        components['cole_component'] = lambda x: cole(x, self.params[0], self.params[2], self.params[3])
        components['lorentzian_component'] = lambda x: lorentzian(x, self.params[1], self.params[4])
        components['lin_component'] = lambda x: x*self.params[5]
        return components
    
class LorentzianColeModel(ComposedDipModel):
    def __init__(self, name: str = None) -> None:
        f = lorentzian_cole
        super().__init__(f, name)
        self.param_names = ['B0_LF_lorentzian', 'B0_HF_cole', 'alpha', 'MFE_LF_lorentzian', 'MFE_HF_cole', 'd_lin']

    def fit(self, x_data, y_data):
        p0: list[float] = [5, 100, 0.5, 2, -1, 1] 
        bounds = ([0, 4, 0, -30, -30, -inf], [100, inf, 1, 30, 30, inf])
        return super().fit(x_data, y_data, p0, bounds)
    
    def get_g(self, tau):
        if len(self.params) == 0:
            return
        B0 = self.params[1]
        alpha = self.params[2]
        return get_g(tau, B0, alpha)
    
    def get_fitted_component_functions(self):
        if not self.fitted:
            logger.error(f'{self.name} not fitted. Run fit first!')
            return
        components = {}
        components['cole_component'] = lambda x: cole(x, self.params[1], self.params[2], self.params[4])
        components['lorentzian_component'] = lambda x: lorentzian(x, self.params[0], self.params[3])
        components['lin_component'] = lambda x: x*self.params[5]
        return components
  
class DoubleColeModel(DipModel):
    def __init__(self, name: str = None) -> None:
        f = double_cole
        super().__init__(f, name)
        self.param_names = ['B0_1', 'B0_2', 'alpha_1', 'alpha_2', 'c']

    def fit(self, x_data, y_data):
        p0: list[float] = [5, 10, 0.6, 0.5, 0]
        bounds = ([0, 5, 0, 0, -inf], [10, 300, 1, 1, inf])
        eps = 0.01
        super().fit(x_data, y_data, p0, bounds)
        # if alpha_2 is low (< eps) the model is likely to be too complex for the given data -> set self.fitted to False to ignore this model 
        if self.fitted and self.params[3] < eps:
            logger.error(f'alpha_2 < double cole eps: model too complex')
            self.fitted = False
            self.params = []
            self.params_err = []
        return
    
    def get_g(self, tau):
        if len(self.params) == 0:
            return
        B0_1 = self.params[0]
        B0_2 = self.params[1] 
        alpha_1 = self.params[2]
        alpha_2 = self.params[3]
        c_pl_mi = self.params[4]
        c = np.absolute(c_pl_mi)
        B0 = ((B0_2 / c) + (1-(1/c)) * B0_1)
        self.params = np.append(self.params, [B0])
        self.param_names = np.append(self.param_names, ['B0'])
        alpha = (alpha_2 + alpha_1) / 2
        self.params = np.append(self.params, [alpha])
        self.param_names = np.append(self.param_names, ['alpha'])
        return get_g(tau, B0, alpha)
    
class NonLorentzianModel(DipModel):
    def __init__(self, name: str = None) -> None:
        f = non_lorentzian
        super().__init__(f, name)
        self.param_names = ['B0', 'MFE_max']

    def fit(self, x_data, y_data):
        p0: list[float] = [0, 2] 
        bounds = ([0, -40], [inf, 40])
        return super().fit(x_data, y_data, p0, bounds)
 
    def get_g(self, tau):
        if len(self.params) == 0:
            return
        raise NotImplementedError(f"g for {self.name} not implemented")
    
class DoubleNonLorentzianModel(DipModel):
    def __init__(self, name: str = None) -> None:
        f = double_non_lorentzian
        super().__init__(f, name)
        self.param_names = ['B0_LF', 'B0_HF', 'MFE_LF', 'MFE_HF']

    def fit(self, x_data, y_data):
        p0: list[float] = [5, 100, 2, -0.1]
        bounds = ([0, 5, -40, -40 ], [50, inf, 40, 40 ])
        return super().fit(x_data, y_data, p0, bounds)
    
    def get_g(self, tau):
        if len(self.params) == 0:
            return
        raise NotImplementedError(f"g for {self.name} not implemented")
    

class LorentzianModel(DipModel):
    def __init__(self, name: str = None) -> None:
        f = lorentzian
        super().__init__(f, name)
        self.param_names = ['B0', 'MFE_max']

    def fit(self, x_data, y_data):
        p0: list[float] = [10, 2]
        bounds = ([0, -40], [inf, 40])
        return super().fit(x_data, y_data, p0, bounds)
    
    def get_g(self, tau):
        if len(self.params) == 0:
            return
        raise NotImplementedError(f"g for {self.name} not implemented")
        

class DoubleLorentzianModel(DipModel):
    def __init__(self, name: str = None) -> None:
        f = double_lorentzian
        super().__init__(f, name)
        self.param_names = ['B0_LF', 'B0_HF', 'MFE_LF', 'MFE_HF']

    def fit(self, x_data, y_data):
        p0: list[float] = [5, 100, 2, -0.1]
        bounds = ([0, 5, -40, -20 ], [50, inf, 40, 20 ])
        return super().fit(x_data, y_data, p0, bounds)

    def get_g(self, tau):
        if len(self.params) == 0:
            return
        raise NotImplementedError(f"g for {self.name} not implemented")

class LorentzianNonLorentzianModel(DipModel):
    def __init__(self, name: str = None) -> None:
        f = lorentzian_non_lorentzian
        super().__init__(f, name)
        self.param_names = ['B0_LF', 'B0_HF', 'MFE_LF', 'MFE_HF']

    def fit(self, x_data, y_data):
        p0: list[float] = [5, 100, 2, -0.1]
        bounds = ([0, 5, -40, -20 ], [50, inf, 40, 20 ])
        return super().fit(x_data, y_data, p0, bounds)
    
    def get_g(self, tau):
        if len(self.params) == 0:
            return
        raise NotImplementedError(f"g for {self.name} not implemented")

class SOC_RISC_Model(DipModel):
    def __init__(self, name: str = None) -> None:
        f = soc_risc
        super().__init__(f, name)
        self.param_names = ['a', 'b', 'c', 'B1', 'B2', 'B3']

    def fit(self, x_data, y_data):
        p0: list[float] = [1, 0.2, 1.5, 8, 65, 45]
        bounds = ([0, 0, 0, 0, 60, 40], [1, 1, 2,  20, 100, 60])
        return super().fit(x_data, y_data, p0, bounds)
    
    def get_g(self, tau):
        if len(self.params) == 0:
            return
        raise NotImplementedError(f"g for {self.name} not implemented")
    
    def get_fitted_component_functions(self):
        if not self.fitted:
            logger.error(f'{self.name} not fitted. Run fit first!')
            return
        components = {}
        components['isc_component'] = lambda x: self.params[0] * (x**2 / (x**2 + (self.params[3])**2))
        components['risc_component'] = lambda x: self.params[1] (x**2 / (x**2 + (self.params[4])**2))
        components['tca_component'] = lambda x: self.params[2] (x**2 / (abs(x) + (params[5]))**2)
        return components