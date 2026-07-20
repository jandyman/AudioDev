from __future__ import annotations
__all__ = ['AttRel', 'AttRelParams', 'AttRelState', 'FollowPeaks', 'FollowPeaksParams', 'FollowPeaksState']
class AttRel:
    params: AttRelParams
    state: AttRelState
    @staticmethod
    def _pybind11_conduit_v1_(*args, **kwargs):
        ...
    def __init__(self) -> None:
        ...
    def init(self) -> None:
        ...
    def proc(self, buffers: list) -> None:
        ...
class AttRelParams:
    attCoef: float
    attTime: float
    fs: float
    relCoef: float
    relTime: float
    @staticmethod
    def _pybind11_conduit_v1_(*args, **kwargs):
        ...
    def __init__(self) -> None:
        ...
class AttRelState:
    lastout: float
    @staticmethod
    def _pybind11_conduit_v1_(*args, **kwargs):
        ...
    def __init__(self) -> None:
        ...
class FollowPeaks:
    params: FollowPeaksParams
    state: FollowPeaksState
    @staticmethod
    def _pybind11_conduit_v1_(*args, **kwargs):
        ...
    def __init__(self) -> None:
        ...
    def init(self) -> None:
        ...
    def proc(self, buffers: list) -> None:
        ...
class FollowPeaksParams:
    attCoef: float
    div: float
    @staticmethod
    def _pybind11_conduit_v1_(*args, **kwargs):
        ...
    def __init__(self) -> None:
        ...
class FollowPeaksState:
    lastout: float
    lastpeak: float
    sampSincePeak: float
    @staticmethod
    def _pybind11_conduit_v1_(*args, **kwargs):
        ...
    def __init__(self) -> None:
        ...
