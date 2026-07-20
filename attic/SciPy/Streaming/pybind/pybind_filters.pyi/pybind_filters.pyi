from __future__ import annotations
import numpy
__all__ = ['BiquadChain', 'BiquadChain64', 'BiquadChain64Params', 'BiquadChain64State', 'BiquadChainParams', 'BiquadChainState', 'XCoupledPolesState']
class BiquadChain:
    params: BiquadChainParams
    state: BiquadChainState
    @staticmethod
    def _pybind11_conduit_v1_(*args, **kwargs):
        ...
    def __init__(self) -> None:
        ...
    def init(self) -> None:
        ...
    def proc(self, buffers: list) -> None:
        ...
class BiquadChain64:
    params: BiquadChain64Params
    state: BiquadChain64State
    @staticmethod
    def _pybind11_conduit_v1_(*args, **kwargs):
        ...
    def __init__(self) -> None:
        ...
    def init(self) -> None:
        ...
    def proc(self, buffers: list) -> None:
        ...
class BiquadChain64Params:
    n_stages: int
    @staticmethod
    def _pybind11_conduit_v1_(*args, **kwargs):
        ...
    def __init__(self) -> None:
        ...
    @property
    def coefs(self) -> numpy.ndarray:
        ...
    @coefs.setter
    def coefs(self, arg1: numpy.ndarray[numpy.float64]) -> None:
        ...
class BiquadChain64State:
    @staticmethod
    def _pybind11_conduit_v1_(*args, **kwargs):
        ...
    def __init__(self) -> None:
        ...
    @property
    def dlybuf(self) -> numpy.ndarray:
        ...
    @dlybuf.setter
    def dlybuf(self, arg1: numpy.ndarray[numpy.float64]) -> None:
        ...
class BiquadChainParams:
    n_stages: int
    @staticmethod
    def _pybind11_conduit_v1_(*args, **kwargs):
        ...
    def __init__(self) -> None:
        ...
    @property
    def coefs(self) -> numpy.ndarray:
        ...
    @coefs.setter
    def coefs(self, arg1: numpy.ndarray[numpy.float32]) -> None:
        ...
class BiquadChainState:
    @staticmethod
    def _pybind11_conduit_v1_(*args, **kwargs):
        ...
    def __init__(self) -> None:
        ...
    @property
    def dlybuf(self) -> numpy.ndarray:
        ...
    @dlybuf.setter
    def dlybuf(self, arg1: numpy.ndarray[numpy.float32]) -> None:
        ...
class XCoupledPolesState:
    a1: float
    a2: float
    s1: float
    s2: float
    @staticmethod
    def _pybind11_conduit_v1_(*args, **kwargs):
        ...
    def __init__(self) -> None:
        ...
