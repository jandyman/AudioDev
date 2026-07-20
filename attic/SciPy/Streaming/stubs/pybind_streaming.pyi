"""
streaming demo plugin
"""
from __future__ import annotations
import numpy
__all__ = ['GainBlock', 'Pin', 'SineBlock', 'SingleChanWrapper', 'add_buffer', 'get_buffer', 'make_vector']
class GainBlock(SingleChanWrapper):
    gain: float
    def __init__(self, arg0: int, arg1: float) -> None:
        ...
class Pin:
    bufsiz: float
    fs: float
    n_channels: float
    def __init__(self) -> None:
        ...
class SineBlock(SingleChanWrapper):
    freq: float
    incr: float
    def __init__(self, arg0: int, arg1: float) -> None:
        ...
class SingleChanWrapper:
    buffers: list[list[float]]
    bufsiz: int
    pins: list[Pin]
    def __init__(self, arg0: int, arg1: int) -> None:
        ...
    def assign_buffer(self, arg0: int, arg1: int, arg2: int) -> None:
        ...
    def init(self) -> None:
        ...
    def proc(self) -> None:
        ...
def add_buffer(bufsize: int) -> int:
    """
    create new buffer in buffer pool
    """
def get_buffer(buf_idx: int) -> numpy.ndarray[numpy.float32]:
    """
    retrieve contents of buffer as numpy array
    """
def make_vector() -> list[float]:
    """
    create vector of floats
    """
