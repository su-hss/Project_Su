"""
Collection of MXNet general functions, wrapped to fit Ivy syntax and signature.
"""

# global
import ivy
_round = round
import logging
import mxnet as _mx
import numpy as _np
import math as _math
from numbers import Number
from operator import mul as _mul
from functools import reduce as _reduce
import multiprocessing as _multiprocessing

# local
from ivy.functional.ivy.core import default_device, default_dtype
from ivy.functional.backends.mxnet.core.device import _callable_dev, dev_to_str


DTYPE_TO_STR = {_np.dtype('int8'): 'int8',
                _np.dtype('int16'): 'int16',
                _np.dtype('int32'): 'int32',
                _np.dtype('int64'): 'int64',
                _np.dtype('uint8'): 'uint8',
                _np.dtype('uint16'): 'uint16',
                _np.dtype('uint32'): 'uint32',
                _np.dtype('uint64'): 'uint64',
                'bfloat16': 'bfloat16',
                _np.dtype('float16'): 'float16',
                _np.dtype('float32'): 'float32',
                _np.dtype('float64'): 'float64',
                _np.dtype('bool'): 'bool',

                _np.int8: 'int8',
                _np.int16: 'int16',
                _np.int32: 'int32',
                _np.int64: 'int64',
                _np.uint8: 'uint8',
                _np.uint16: 'uint16',
                _np.uint32: 'uint32',
                _np.uint64: 'uint64',
                _np.float16: 'float16',
                _np.float32: 'float32',
                _np.float64: 'float64',
                _np.bool_: 'bool'}

DTYPE_FROM_STR = {'int8': _np.int8,
                'int16': _np.int16,
                'int32': _np.int32,
                'int64': _np.int64,
                'uint8': _np.uint8,
                'uint16': _np.uint16,
                'uint32': _np.uint32,
                'uint64': _np.uint64,
                'bfloat16': 'bfloat16',
                'float16': _np.float16,
                'float32': _np.float32,
                'float64': _np.float64,
                'bool': _np.bool_}


# API #
# ----#

def array(object_in, dtype=None, dev=None):
    cont = _mxnet_init_context(default_device(dev))
    return _mx.nd.array(object_in, cont, dtype=default_dtype(dtype, object_in))


asarray = array


def is_array(x, exclusive=False):
    if isinstance(x, _mx.ndarray.ndarray.NDArray):
        if exclusive and x.grad is not None:
            return False
        return True
    return False


copy_array = lambda x: x.copy()


@_handle_flat_arrays_in_out
def array_equal(x0, x1):
    if ivy.dtype(x0, as_str=True) == 'bool':
        x0 = x0.astype('int32')
    if ivy.dtype(x1, as_str=True) == 'bool':
        x1 = x1.astype('int32')
    return _mx.nd.min(_mx.nd.broadcast_equal(x0, x1)) == 1


def dtype_bits(dtype_in):
    dtype_str = dtype_to_str(dtype_in)
    if 'bool' in dtype_str:
        return 1
    return int(dtype_str.replace("<class 'numpy.", '').replace("'>", '').replace('uint', '').replace(
        'int', '').replace('bfloat', '').replace('float', ''))


equal = lambda x1, x2: x1 == x2
equal.__name__ = 'equal'
to_numpy = lambda x: x if isinstance(x, _np.ndarray) else (_np.array(x) if isinstance(x, (int, float)) else x.asnumpy())
to_numpy.__name__ = 'to_numpy'
to_scalar = lambda x: x if isinstance(x, Number) else x.asscalar().item()
to_scalar.__name__ = 'to_scalar'
to_list = lambda x: to_numpy(x).tolist()
to_list.__name__ = 'to_list'
shape = lambda x, as_tensor=False: _mx.nd.shape_array(x) if as_tensor else x.shape
shape.__name__ = 'shape'
get_num_dims = lambda x, as_tensor=False:\
    _mx.nd.shape_array(_mx.nd.shape_array(x)).reshape([]) if as_tensor else len(x.shape)
minimum = lambda x, y: _mx.nd.array(_mx.nd.minimum(_scalar_or_flat_array_to_scalar(x), _scalar_or_flat_array_to_scalar(y)))
maximum = lambda x, y: _mx.nd.array(_mx.nd.maximum(_scalar_or_flat_array_to_scalar(x), _scalar_or_flat_array_to_scalar(y)))


@_handle_flat_arrays_in_out
def clip(x, x_min, x_max):
    return _mx.nd.clip(_mx.nd.array(x), x_min, x_max)


@_handle_flat_arrays_in_out
def round(x):
    return _mx.nd.round(x)


@_handle_flat_arrays_in_out
def floormod(x, y):
    return x % y


@_handle_flat_arrays_in_out
def floor(x):
    return _mx.nd.floor(x)


@_handle_flat_arrays_in_out
def ceil(x):
    return _mx.nd.ceil(x)


# noinspection PyShadowingBuiltins
@_handle_flat_arrays_in_out
def abs(x):
    return _mx.nd.abs(x)


argmax = lambda x, axis=0: _mx.nd.argmax(x, axis)
argmin = lambda x, axis=0: _mx.nd.argmin(x, axis)


@_handle_flat_arrays_in_out
def cast(x, dtype):
    return x.astype(dtype)


astype = cast


# noinspection PyUnresolvedReferences
def arange(stop, start=0, step=1, dtype=None, dev=None):
    cont = _mxnet_init_context(default_device(dev))
    stop = stop if isinstance(stop, Number) else stop.asscalar()
    start = start if isinstance(start, Number) else start.asscalar()
    step = step if isinstance(step, Number) else step.asscalar()
    return _mx.nd.arange(start, stop, ctx=cont, step=step, dtype=dtype)


def _linspace(start, stop, num, cont):
    if num == 1:
        return start
    start = _mx.nd.array(start).reshape((1,)).astype('float32')
    stop = _mx.nd.array(stop).reshape((1,)).astype('float32')
    n_m_1 = _mx.nd.array(num - 1).reshape((1,)).astype('float32')
    increment = (stop - start)/n_m_1
    increment_tiled = _mx.nd.tile(increment, num - 1)
    increments = increment_tiled * _mx.nd.array(_mx.nd.np.linspace(1, num - 1, num - 1).tolist(), ctx=cont)
    ret = _mx.nd.concat(start, start + increments, dim=0)
    return ret


def linspace(start, stop, num, axis=None, dev=None):
    cont = _mxnet_init_context(default_device(dev))
    num = num.asnumpy()[0] if isinstance(num, _mx.nd.NDArray) else num
    start_is_array = isinstance(start, _mx.nd.NDArray)
    stop_is_array = isinstance(stop, _mx.nd.NDArray)
    start_shape = []
    if start_is_array:
        start_shape = list(start.shape)
        start = start.reshape((-1,))
    if stop_is_array:
        start_shape = list(stop.shape)
        stop = stop.reshape((-1,))
    if start_is_array and stop_is_array:
        res = [_linspace(strt, stp, num, cont) for strt, stp in zip(start, stop)]
    elif start_is_array and not stop_is_array:
        res = [_linspace(strt, stop, num, cont) for strt in start]
    elif not start_is_array and stop_is_array:
        res = [_linspace(start, stp, num, cont) for stp in stop]
    else:
        return _linspace(start, stop, num, cont)
    new_shape = start_shape + [num]
    res = _mx.nd.concat(*res, dim=-1).reshape(new_shape)
    if axis is not None:
        res = _mx.nd.swapaxes(res, axis, -1)
    return res


def logspace(start, stop, num, base=10., axis=None, dev=None):
    power_seq = linspace(start, stop, num, axis, default_device(dev))
    return base ** power_seq


@_handle_flat_arrays_in_out
def concatenate(xs, axis=-1):
    return _mx.nd.concat(*xs, dim=axis)


def stack(xs, axis=0):
    if xs[0].shape == ():
        return _mx.nd.reshape(_mx.nd.stack(*[_flat_array_to_1_dim_array(x) for x in xs], axis=axis), -1)
    return _mx.nd.stack(*xs, axis=axis)


def unstack(x, axis, keepdims=False):
    if x.shape == ():
        return [x]
    num_outputs = x.shape[axis]
    ret = _mx.nd.split(x, num_outputs, axis, squeeze_axis=not keepdims)
    return ret if isinstance(ret, list) else [ret]


def split(x, num_or_size_splits=None, axis=0, with_remainder=False):
    if x.shape == ():
        if num_or_size_splits is not None and num_or_size_splits != 1:
            raise Exception('input array had no shape, but num_sections specified was {}'.format(num_or_size_splits))
        return [x]
    if num_or_size_splits == 1:
        return [x]
    elif with_remainder and isinstance(num_or_size_splits, int):
        num_or_size_splits = x.shape[axis] if not num_or_size_splits else num_or_size_splits
        num_chunks = x.shape[axis] / num_or_size_splits
        num_chunks_int = _math.floor(num_chunks)
        remainder_size = int((num_chunks - num_chunks_int) * num_or_size_splits)
        num_or_size_splits = [num_or_size_splits]*num_chunks_int + [remainder_size]
    if isinstance(num_or_size_splits, (list, tuple)):
        csum = [0] + _np.cumsum(num_or_size_splits).tolist()
        starts = csum[:-1]
        ends = csum[1:]
        if axis < 0:
            slices = [tuple([Ellipsis, slice(s, e, 1)] + [slice(None, None, None)]*int(abs(axis)-1))
                      for s, e in zip(starts, ends)]
        else:
            slices = [tuple([slice(None, None, None)]*axis + [slice(s, e, 1)])
                      for s, e in zip(starts, ends)]
        return [x[so] for so in slices]
    return _mx.nd.split(x, x.shape[axis] if not num_or_size_splits else num_or_size_splits, axis)


@_handle_flat_arrays_in_out
def repeat(x, repeats, axis=None):
    return _mx.nd.repeat(x, repeats, axis)


def tile(x, reps):
    if isinstance(reps, _mx.nd.ndarray.NDArray):
        reps = reps.asnumpy().tolist()
    return _mx.nd.tile(_flat_array_to_1_dim_array(x), reps)


@_handle_flat_arrays_in
def constant_pad(x, pad_width, value=0):
    if isinstance(pad_width, _mx.ndarray.ndarray.NDArray):
        pad_width = pad_width.asnumpy().tolist()
    x_shape = list(x.shape)
    num_dims = len(x_shape)
    if num_dims > 3:
        raise Exception('Invalid inputs. Pad for mxnet only supports inputs with 3 dimensions or smaller.')
    num_dims_to_add = 4 - num_dims
    new_shape = tuple([1] * num_dims_to_add + x_shape)
    mat_expanded_dims = _mx.nd.reshape(x, new_shape)
    pad_width_flat = [0]*num_dims_to_add*2 + [item for sublist in pad_width for item in sublist]
    pad_expanded_dims = _mx.nd.pad(mat_expanded_dims, mode="constant", pad_width=tuple(pad_width_flat),
                                   constant_value=value)
    new_shape = [orig_dim + pad_width_item[0] + pad_width_item[1] for orig_dim, pad_width_item in zip(x_shape, pad_width)]
    res = _mx.nd.reshape(pad_expanded_dims, tuple(new_shape))
    return res


def zero_pad(x, pad_width):
    return constant_pad(x, pad_width, 0)


swapaxes = _mx.nd.swapaxes


def transpose(x, axes=None):
    if axes is None:
        num_dims = len(x.shape)
        axes = list(range(num_dims))
        axes.reverse()
    return _mx.nd.transpose(x, axes)


def expand_dims(x, axis):
    if x.shape == ():
        return _flat_array_to_1_dim_array(x)
    return _mx.nd.expand_dims(x, axis)


@_handle_flat_arrays_in_out
def where(condition, x1, x2):
    x_shape = list(x1.shape)
    condition_shape = list(condition.shape)
    if x_shape == condition_shape:
        res = _mx.nd.where(condition, x1, x2)
        return res
    tile_reps = [int(x / c) for x, c in zip(x_shape, condition_shape)]
    tiled_condition = _mx.nd.tile(condition, tile_reps)
    return _mx.nd.where(tiled_condition, x1, x2)


def indices_where(x):
    x_shape = x.shape
    x_flat = x.reshape((1, -1,))
    flat_indices = x_flat.astype('int32').tostype('csr').indices
    if flat_indices.shape == (0,):
        res = flat_indices.reshape((0, len(x_shape)))
        return res
    res = _mx.nd.swapaxes(_mx.nd.unravel_index(flat_indices, x_shape), 0, 1)
    return res


@_handle_flat_arrays_in_out
def isinf(x):
    return _mx.nd.contrib.isinf(x).astype('bool')


reshape = lambda x, new_shape: x.reshape(new_shape)


def squeeze(x, axis=None):
    if x.shape == ():
        if axis is None or axis == 0 or axis == -1:
            return x
        raise Exception('tried to squeeze a zero-dimensional input by axis {}'.format(axis))
    res = _mx.nd.squeeze(x, axis)
    if axis is None:
        return _1_dim_array_to_flat_array(res)
    return res


# noinspection PyShadowingNames



def zeros_like(x, dtype=None, dev=None):
    if x.shape == ():
        return _mx.nd.array(0., ctx=_mxnet_init_context(default_device(dev)))
    mx_zeros = _mx.nd.zeros_like(x, ctx=_mxnet_init_context(default_device(dev)))
    return mx_zeros if not dtype else mx_zeros.astype(dtype)


def full(shape, fill_value, dtype=None, device=None):
    shape = ivy.shape_to_tuple(shape)
    cont = _mxnet_init_context(default_device(device))
    if len(shape) == 0 or 0 in shape:
        return _1_dim_array_to_flat_array(
            _mx.nd.full((1,), fill_value, cont, dtype_from_str(default_dtype(dtype, fill_value))))
    return _mx.nd.full(shape, fill_value, cont, dtype_from_str(default_dtype(dtype, fill_value)))


def ones_like(x, dtype=None, dev=None):
    if x.shape == ():
        return _mx.nd.array(1., ctx=_mxnet_init_context(default_device(dev)))
    mx_ones = _mx.nd.ones_like(x, ctx=_mxnet_init_context(default_device(dev)))
    return mx_ones if dtype is None else mx_ones.astype(dtype)


# noinspection PyUnusedLocal
one_hot = lambda indices, depth, dev=None: _mx.nd.one_hot(indices, depth)


def cross(x1, x2):
    a1 = x1[..., 0:1]
    a2 = x1[..., 1:2]
    a3 = x1[..., 2:3]
    b1 = x2[..., 0:1]
    b2 = x2[..., 1:2]
    b3 = x2[..., 2:3]
    res1 = a2*b3 - a3*b2
    res2 = a3*b1 - a1*b3
    res3 = a1*b2 - a2*b1
    res = _mx.nd.concat(res1, res2, res3, dim=-1)
    return res


def matmul(x1, x2):
    expanded = False
    x1_shape = list(x1.shape)
    x2_shape = list(x2.shape)
    if len(x1_shape) != 3:
        num_x1_dims = len(x1_shape)
        x1 = _mx.nd.reshape(x1, [1]*max(2-num_x1_dims, 0) + [-1] + x1_shape[-min(num_x1_dims, 2):])
        expanded = True
    if len(x2_shape) != 3:
        num_x2_dims = len(x2_shape)
        x2 = _mx.nd.reshape(x2, [1]*max(2-num_x2_dims, 0) + [-1] + x2_shape[-min(num_x2_dims, 2):])
        expanded = True
    x1_batch_size = x1.shape[0]
    x2_batch_size = x2.shape[0]
    if x1_batch_size > x2_batch_size:
        x2 = _mx.nd.tile(x2, (int(x1_batch_size/x2_batch_size), 1, 1))
    elif x2_batch_size > x1_batch_size:
        x1 = _mx.nd.tile(x1, (int(x2_batch_size / x1_batch_size), 1, 1))
    res = _mx.nd.batch_dot(x1, x2)
    if expanded:
        return _mx.nd.reshape(res, list(x1_shape[:-1]) + [res.shape[-1]])
    return res


cumsum = lambda x, axis=0: _mx.nd.cumsum(x, axis if axis >= 0 else axis % len(x.shape))


def cumprod(x, axis=0, exclusive=False):
    array_stack = [_mx.nd.expand_dims(chunk, axis) for chunk in unstack(x, axis)]
    if exclusive:
        array_stack = [_mx.nd.ones_like(array_stack[0])] + array_stack[:-1]
    new_array_list = [array_stack[0]]
    for array_chunk in array_stack[1:]:
        new_array_list.append(new_array_list[-1] * array_chunk)
    return _mx.nd.concat(*new_array_list, dim=axis)


def identity(n, dtype='float32', batch_shape=None, dev=None):
    mat = _mx.nd.eye(n, dtype=dtype).copyto(_mxnet_init_context(default_device(dev)))
    if batch_shape is None:
        return mat
    else:
        reshape_dims = [1]*len(batch_shape) + [n, n]
        tile_dims = list(batch_shape) + [1, 1]
        res = _mx.nd.tile(_mx.nd.reshape(mat, reshape_dims), tile_dims)
        return res


def meshgrid(*xs, indexing='ij'):
    # ToDo: implement this without reliance on NumPy backend
    xs_np = [x.as_np_ndarray() for x in xs]
    return tuple([item.as_nd_ndarray() for item in _mx.np.meshgrid(*xs_np, indexing=indexing)])


# noinspection PyShadowingNames
def scatter_flat(indices, updates, size=None, tensor=None, reduction='sum', dev=None):
    if ivy.exists(tensor):
        raise Exception('MXNet scatter_flat does not support scattering into an pre-existing tensor.')
    if reduction == 'replace':
        return _mx.nd.scatter_nd(updates, _mx.nd.expand_dims(indices, 0), [size]).copyto(_mxnet_init_context(default_device(dev)))
    else:
        raise Exception('MXNet scatter_flat currently only supports reduction mode "replace", but {} selected.'.
                        format(reduction))


# noinspection PyShadowingNames
def scatter_nd(indices, updates, shape=None, tensor=None, reduction='sum', dev=None):
    if ivy.exists(tensor):
        raise Exception('MXNet scatter_flat does not support scattering into an pre-existing tensor.')
    if dev is None:
        dev = _callable_dev(indices)
    shape = list(shape)
    num_idx_dims = len(indices.shape)
    transpose_order = [num_idx_dims-1] + list(range(num_idx_dims-1))
    indices = _mx.nd.transpose(indices, transpose_order)
    shape = shape if type(shape) is list else shape.asnumpy().astype(_np.int32).tolist()
    if reduction == 'replace':
        return _mx.nd.scatter_nd(updates, indices, shape).copyto(_mxnet_init_context(dev))
    else:
        raise Exception('MXNet scatter_nd currently only supports reduction mode "replace", but {} selected.'.
                        format(reduction))


def gather(params, indices, axis=-1, dev=None):
    if dev is None:
        dev = _callable_dev(params)
    index_slices = unstack(indices, -1)
    res = _mx.nd.concat(
        *[_mx.nd.expand_dims(_mx.nd.pick(params, idx_slice, axis), -1) for idx_slice in index_slices], dim=-1)
    res = _mx.nd.reshape(res, indices.shape)
    return res.copyto(_mxnet_init_context(dev))


def gather_nd(params, indices, dev=None):
    if dev is None:
        dev = _callable_dev(params)
    indices_shape = indices.shape
    num_idx_dims = len(indices_shape)
    transpose_order = [num_idx_dims-1] + list(range(num_idx_dims-1))
    indices = _mx.nd.transpose(indices, transpose_order)
    return _mx.nd.gather_nd(params, indices).copyto(_mxnet_init_context(dev))


def linear_resample(x, num_samples, axis=-1):
    x_shape = list(x.shape)
    num_x_dims = len(x_shape)
    axis = axis % num_x_dims
    x_pre_shape = x_shape[0:axis]
    x_pre_size = _reduce(_mul, x_pre_shape) if x_pre_shape else 1
    num_pre_dims = len(x_pre_shape)
    num_vals = x.shape[axis]
    x_post_shape = x_shape[axis+1:]
    x_post_size = _reduce(_mul, x_post_shape) if x_post_shape else 1
    num_post_dims = len(x_post_shape)
    xp = _mx.nd.reshape(_mx.nd.arange(num_vals*x_pre_size*x_post_size), x_shape)
    x_coords = _mx.nd.arange(num_samples) * ((num_vals-1)/(num_samples-1)) * x_post_size
    x_coords = _mx.nd.reshape(x_coords, [1]*num_pre_dims + [num_samples] + [1]*num_post_dims)
    x_coords = _mx.nd.broadcast_to(x_coords, x_pre_shape + [num_samples] + x_post_shape)
    slc = [slice(None)] * num_x_dims
    slc[axis] = slice(0, 1, 1)
    x_coords = x_coords + xp[tuple(slc)]
    x = _mx.nd.reshape(x, (-1,))
    xp = _mx.nd.reshape(xp, (-1,))
    x_coords = _mx.nd.reshape(x_coords, (-1,))
    ret = _mx.nd.array(_mx.np.interp(x_coords.asnumpy(), xp.asnumpy(), x.asnumpy()))
    return _mx.nd.reshape(ret, x_pre_shape + [num_samples] + x_post_shape)


def dtype(x, as_str=False):
    dt = x.dtype
    if as_str:
        return dtype_to_str(dt)
    return x.dtype


def dtype_to_str(dtype_in):
    if isinstance(dtype_in, str):
        return dtype_in
    return DTYPE_TO_STR[dtype_in]


def dtype_from_str(dtype_in):
    if not isinstance(dtype_in, str):
        return dtype_in
    return DTYPE_FROM_STR[dtype_in]


# noinspection PyUnusedLocal
def compile(func, dynamic=True, example_inputs=None, static_argnums=None, static_argnames=None):
    logging.warning('MXnet does not support compiling arbitrary functions, '
                    'consider writing a function using MXNet Symbolic backend instead for compiling.\n'
                    'Now returning the unmodified function.')
    return func


current_framework_str = lambda: 'mxnet'
current_framework_str.__name__ = 'current_framework_str'
multiprocessing = lambda context=None: _multiprocessing if context is None else _multiprocessing.get_context(context)
container_types = lambda: []


def inplace_update(x, val):
    if x.shape == ():
        raise Exception('MXNet does not support inplace updates of 0-dimensional arrays')
    x[:] = val
    return x


def inplace_decrement(x, val):
    if x.shape == ():
        raise Exception('MXNet does not support inplace updates of 0-dimensional arrays')
    x -= val
    return x


def inplace_increment(x, val):
    if x.shape == ():
        raise Exception('MXNet does not support inplace updates of 0-dimensional arrays')
    x += val
    return x


inplace_arrays_supported = lambda: True
inplace_variables_supported = lambda: True
