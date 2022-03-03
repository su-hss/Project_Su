# global
import numpy as np
import  jax
import jaxlib
import jax.numpy as jnp
from typing import Union
from jaxlib.xla_extension import Buffer
# local
import ivy
JaxArray = Union[jax.interpreters.xla._DeviceArray, jaxlib.xla_extension.DeviceArray, Buffer]
# noinspection PyShadowingBuiltins
def iinfo(type: Union[jnp.dtype, str, JaxArray]) \
        -> np.iinfo:
    return jnp.iinfo(ivy.dtype_from_str(type))


class Finfo:

    def __init__(self, jnp_finfo):
        self._jnp_finfo = jnp_finfo

    @property
    def bits(self):
        return self._jnp_finfo.bits

    @property
    def eps(self):
        return float(self._jnp_finfo.eps)

    @property
    def max(self):
        return float(self._jnp_finfo.max)

    @property
    def min(self):
        return float(self._jnp_finfo.min)

    @property
    def smallest_normal(self):
        return float(self._jnp_finfo.tiny)


# noinspection PyShadowingBuiltins
def finfo(type: Union[jnp.dtype, str, JaxArray]) \
        -> Finfo:
    return Finfo(jnp.finfo(ivy.dtype_from_str(type)))


def broadcast_to(x: JaxArray, new_shape) -> JaxArray:
    return jnp.broadcast_to(x, new_shape)
