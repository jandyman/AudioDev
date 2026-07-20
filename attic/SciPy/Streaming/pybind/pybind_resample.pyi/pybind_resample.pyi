from __future__ import annotations
import numpy
__all__ = ['DelayBuf', 'DelayBufState', 'JosFractDelay', 'JosFractDelayParams', 'Resampler', 'ResamplerState']
class DelayBuf:
    state: DelayBufState
    @staticmethod
    def _pybind11_conduit_v1_(*args, **kwargs):
        ...
    def __init__(self) -> None:
        ...
    def get_values(self, delay: int, output: numpy.ndarray[numpy.float32]) -> None:
        ...
    def push(self, samples: numpy.ndarray[numpy.float32]) -> None:
        ...
class DelayBufState:
    wr_idx: int
    @staticmethod
    def _pybind11_conduit_v1_(*args, **kwargs):
        ...
    def __init__(self) -> None:
        ...
    @property
    def data(self) -> numpy.ndarray:
        ...
    @data.setter
    def data(self, arg1: numpy.ndarray[numpy.float32]) -> None:
        ...
class JosFractDelay:
    params: JosFractDelayParams
    @staticmethod
    def _pybind11_conduit_v1_(*args, **kwargs):
        ...
    def __init__(self) -> None:
        ...
    def fixed_delay(self, arg0: DelayBuf, arg1: float) -> float:
        ...
class JosFractDelayParams:
    allow_overflow: bool
    h_coef_set: list
    oversamp_bits: int
    @staticmethod
    def _pybind11_conduit_v1_(*args, **kwargs):
        ...
    def __init__(self) -> None:
        ...
    @property
    def buffer(self) -> numpy.ndarray:
        ...
    @buffer.setter
    def buffer(self, arg1: numpy.ndarray[numpy.float32]) -> None:
        ...
class Resampler:
    state: ResamplerState
    @staticmethod
    def _pybind11_conduit_v1_(*args, **kwargs):
        ...
    def __init__(self) -> None:
        ...
    def proc(self, bufs: list) -> None:
        ...
class ResamplerState:
    dly_buf: DelayBuf
    frac_dly: JosFractDelay
    @staticmethod
    def _pybind11_conduit_v1_(*args, **kwargs):
        ...
    def __init__(self) -> None:
        ...
