"""
Collection of PyTorch general functions, wrapped to fit Ivy syntax and signature.
"""

# global
import ivy
import numpy as np
torch_scatter = None
import math as _math
import torch as _torch
from operator import mul
from torch.types import Number
from functools import reduce as _reduce
from typing import List, Dict, Optional, Union

# local
from ivy.functional.ivy.core import default_device, default_dtype
from ivy.functional.backends.torch.core.device import dev_from_str, _callable_dev

# API #
# ----#


# noinspection PyShadowingNames
def array(object_in, dtype: Optional[str] = None, dev: Optional[str] = None):
    dev = default_device(dev)
    dtype = dtype_from_str(default_dtype(dtype, object_in))
    if isinstance(object_in, np.ndarray):
        return _torch.Tensor(object_in).to(dev_from_str(dev))
    if dtype is not None:
        return _torch.tensor(object_in, dtype=dtype, device=dev_from_str(dev))
    elif isinstance(object_in, _torch.Tensor):
        return object_in.to(dev_from_str(dev))
    else:
        return _torch.tensor(object_in, device=dev_from_str(dev))


asarray = array


def is_array(x, exclusive=False):
    if isinstance(x, _torch.Tensor):
        if exclusive and x.requires_grad:
            return False
        return True
    return False


def copy_array(x):
    return x.clone()


def array_equal(x0, x1):
    return _torch.equal(x0, x1)


def dtype_bits(dtype_in):
    dtype_str = dtype_to_str(dtype_in)
    if 'bool' in dtype_str:
        return 1
    return int(dtype_str.replace('torch.', '').replace('uint', '').replace('int', '').replace('bfloat', '').replace(
        'float', ''))


def equal(x1, x2):
    x1_bits = dtype_bits(x1.dtype)
    if isinstance(x2, (int, float, bool)):
        return x1 == x2
    x2_bits = dtype_bits(x2.dtype)
    if x1_bits > x2_bits:
        x2 = x2.type(x1.dtype)
    elif x2_bits > x1_bits:
        x1 = x1.type(x2.dtype)
    return x1 == x2


def to_numpy(x) -> np.ndarray:
    if isinstance(x, np.ndarray) or isinstance(x, (float, int, bool)):
        return x
    elif _torch.is_tensor(x):
        return x.detach().cpu().numpy()
    raise ValueError('Expected a pytroch tensor.')


def to_scalar(x) -> Union[float, int, bool]:
    if isinstance(x, (float, int)):
        return x
    return x.item()


def to_list(x):
    if isinstance(x, np.ndarray):
        return x.tolist()
    elif _torch.is_tensor(x):
        return x.detach().cpu().tolist()
    raise ValueError('Expected a pytroch tensor.')


def shape(x, as_tensor=False) -> Union[_torch.Tensor, List[int]]:
    return _torch.tensor(x.shape) if as_tensor else x.shape


def get_num_dims(x, as_tensor=False) -> Union[_torch.Tensor, int]:
    return _torch.tensor(len(x.shape)) if as_tensor else len(x.shape)


def minimum(x, y):
    x_val = _torch.tensor(x) if (isinstance(x, int) or isinstance(x, float)) else x
    y_val = _torch.tensor(y) if (isinstance(y, int) or isinstance(y, float)) else y
    return _torch.min(x_val, y_val)


def maximum(x, y):
    x_val = _torch.tensor(x) if (isinstance(x, int) or isinstance(x, float)) else x
    y_val = _torch.tensor(y) if (isinstance(y, int) or isinstance(y, float)) else y
    return _torch.max(x_val, y_val)


def clip(x, x_min, x_max):
    return _torch.clamp(x, x_min, x_max)


# noinspection PyShadowingBuiltins
def round(x):
    return _torch.round(x)


def floormod(x, y):
    return x % y


def floor(x):
    return _torch.floor(x)


def ceil(x):
    return _torch.ceil(x)


# noinspection PyShadowingBuiltins
def abs(x):
    return _torch.abs(x)


def argmax(x, axis: int = 0):
    ret = _torch.argmax(x, axis)
    if ret.shape == ():
        return ret.reshape(-1)
    return ret


def argmin(x, axis: int = 0):
    ret = _torch.argmin(x, axis)
    if ret.shape == ():
        return ret.reshape(-1)
    return ret


def cast(x, dtype_in: str):
    dtype_val = dtype_from_str(dtype_in)
    return x.type(dtype_val)


astype = cast


# noinspection PyShadowingNames
def arange(stop: Number, start: Number = 0, step: Number = 1, dtype: Optional[str] = None,
           dev: Optional[str] = None):
    dev = default_device(dev)
    if dtype is not None:
        return _torch.arange(start, stop, step=step, dtype=dtype_from_str(dtype), device=dev_from_str(dev))
    else:
        return _torch.arange(start, stop, step=step, device=dev_from_str(dev))


def _differentiable_linspace(start, stop, num, device):
    if num == 1:
        return _torch.unsqueeze(start, 0)
    n_m_1 = num - 1
    increment = (stop - start) / n_m_1
    increment_tiled = increment.repeat(n_m_1)
    increments = increment_tiled * _torch.linspace(1, n_m_1, n_m_1, device=device)
    res = _torch.cat((_torch.unsqueeze(_torch.tensor(start), 0), start + increments), 0)
    return res


# noinspection PyUnboundLocalVariable,PyShadowingNames
def linspace(start, stop, num, axis=None, dev=None):
    num = num.detach().numpy().item() if isinstance(num, _torch.Tensor) else num
    start_is_array = isinstance(start, _torch.Tensor)
    stop_is_array = isinstance(stop, _torch.Tensor)
    linspace_method = _torch.linspace
    dev = default_device(dev)
    sos_shape = []
    if start_is_array:
        start_shape = list(start.shape)
        sos_shape = start_shape
        if num == 1:
            return start.unsqueeze(axis).to(dev_from_str(dev))
        start = start.reshape((-1,))
        linspace_method = _differentiable_linspace if start.requires_grad else _torch.linspace
    if stop_is_array:
        stop_shape = list(stop.shape)
        sos_shape = stop_shape
        if num == 1:
            return _torch.ones(stop_shape[:axis] + [1] + stop_shape[axis:], device=dev_from_str(dev)) * start
        stop = stop.reshape((-1,))
        linspace_method = _differentiable_linspace if stop.requires_grad else _torch.linspace
    if start_is_array and stop_is_array:
        if num < start.shape[0]:
            start = start.unsqueeze(-1)
            stop = stop.unsqueeze(-1)
            diff = stop - start
            inc = diff / (num-1)
            res = [start]
            res += [start + inc*i for i in range(1, num-1)]
            res.append(stop)
        else:
            res = [linspace_method(strt, stp, num, device=dev_from_str(dev)) for strt, stp in zip(start, stop)]
        _torch.cat(res, -1).reshape(start_shape + [num])
    elif start_is_array and not stop_is_array:
        if num < start.shape[0]:
            start = start.unsqueeze(-1)
            diff = stop - start
            inc = diff / (num - 1)
            res = [start]
            res += [start + inc * i for i in range(1, num - 1)]
            res.append(_torch.ones_like(start, device=dev_from_str(dev)) * stop)
        else:
            res = [linspace_method(strt, stop, num, device=dev_from_str(dev)) for strt in start]
    elif not start_is_array and stop_is_array:
        if num < stop.shape[0]:
            stop = stop.unsqueeze(-1)
            diff = stop - start
            inc = diff / (num - 1)
            res = [_torch.ones_like(stop, device=dev_from_str(dev)) * start]
            res += [start + inc * i for i in range(1, num - 1)]
            res.append(stop)
        else:
            res = [linspace_method(start, stp, num, device=dev_from_str(dev)) for stp in stop]
    else:
        return linspace_method(start, stop, num, device=dev_from_str(dev))
    res = _torch.cat(res, -1).reshape(sos_shape + [num])
    if axis is not None:
        res = _torch.transpose(res, axis, -1)
    return res.to(dev_from_str(dev))


def logspace(start, stop, num, base=10., axis=None, dev=None):
    power_seq = linspace(start, stop, num, axis, default_device(dev))
    return base ** power_seq


def concatenate(xs: List[_torch.Tensor], axis: int = -1):
    if xs[0].shape == ():
        return _torch.cat([x.unsqueeze(0) for x in xs], axis)
    return _torch.cat(xs, axis)


def stack(xs: List[_torch.Tensor], axis: int = 0):
    return _torch.stack(xs, axis)


def unstack(x, axis: int, keepdims: bool = False) -> List[_torch.Tensor]:
    if x.shape == ():
        return [x]
    ret = list(_torch.unbind(x, axis))
    if keepdims:
        return [r.unsqueeze(axis) for r in ret]
    return ret


def split(x, num_or_size_splits: Optional[Union[int, List[int]]] = None, axis: int = 0, with_remainder: bool = False)\
        -> List[_torch.Tensor]:
    if x.shape == ():
        if num_or_size_splits is not None and num_or_size_splits != 1:
            raise Exception('input array had no shape, but num_sections specified was {}'.format(num_or_size_splits))
        return [x]
    dim_size: int = x.shape[axis]
    if num_or_size_splits is None:
        # noinspection PyUnboundLocalVariable
        num_or_size_splits = 1
    elif isinstance(num_or_size_splits, int):
        if with_remainder:
            num_chunks = x.shape[axis] / num_or_size_splits
            num_chunks_int = _math.floor(num_chunks)
            remainder = num_chunks - num_chunks_int
            if remainder == 0:
                num_or_size_splits = _torch.round(_torch.tensor(dim_size) / _torch.tensor(num_or_size_splits))
            else:
                num_or_size_splits = tuple([num_or_size_splits] * num_chunks_int + [int(remainder*num_or_size_splits)])
        else:
            num_or_size_splits = _torch.round(_torch.tensor(dim_size) / _torch.tensor(num_or_size_splits))
    elif isinstance(num_or_size_splits, list):
        num_or_size_splits = tuple(num_or_size_splits)
    return list(_torch.split(x, num_or_size_splits, axis))


def repeat(x, repeats: Union[int, List[int]], axis: int = None):
    if len(x.shape) == 0 and axis in [0, -1]:
        axis = None
    return _torch.repeat_interleave(x, repeats, axis)


def tile(x, reps):
    if isinstance(reps, _torch.Tensor):
        reps = reps.detach().cpu().numpy().tolist()
    return x.repeat(reps)


# noinspection PyUnresolvedReferences
def constant_pad(x, pad_width: List[List[int]], value: Number = 0.):
    if x.shape == ():
        x = x.unsqueeze(0)
    if isinstance(pad_width, _torch.Tensor):
        pad_width = pad_width.detach().cpu().numpy().tolist()
    pad_width.reverse()
    pad_width_flat: List[int] = list()
    for pad_width_sec in pad_width:
        for item in pad_width_sec:
            pad_width_flat.append(item)
    return _torch.nn.functional.pad(x, pad_width_flat, mode='constant', value=value)


def zero_pad(x, pad_width: List[List[int]]):
    return constant_pad(x, pad_width, 0.)


def swapaxes(x, axis0: int, axis1: int):
    return _torch.transpose(x, axis0, axis1)


def transpose(x, axes: List[int]):
    if axes is None:
        num_dims = len(x.shape)
        axes = list(range(num_dims))
        axes.reverse()
    return x.permute(axes)


def expand_dims(x, axis: int):
    return _torch.unsqueeze(x, axis)


def where(condition, x1, x2):
    return _torch.where(condition.type(_torch.bool), x1, x2)


def indices_where(x):
    where_x = _torch.where(x)
    res = _torch.cat([_torch.unsqueeze(item, -1) for item in where_x], -1)
    return res


def isinf(x):
    return _torch.isinf(x)

def reshape(x, newshape: List[int]):
    if isinstance(newshape, int):
        newshape = [newshape]
    return _torch.reshape(x, newshape)



def squeeze(x, axis: Optional[int] = None):
    if axis is None:
        return _torch.squeeze(x)
    return _torch.squeeze(x, axis)




# noinspection PyShadowingNames
def zeros_like(x, dtype: Optional[str] = None, dev: Optional[str] = None):
    if dev is None:
        dev = _callable_dev(x)
    if dtype is not None:
        type_dict: Dict[str, _torch.dtype] = {'int8': _torch.int8,
            'int16': _torch.int16,
            'int32': _torch.int32,
            'int64': _torch.int64,
            'uint8': _torch.uint8,
            'bfloat16': _torch.bfloat16,
            'float16': _torch.float16,
            'float32': _torch.float32,
            'float64': _torch.float64,
            'bool': _torch.bool}
        return _torch.zeros_like(x, dtype=type_dict[dtype], device=dev_from_str(dev))
    return _torch.zeros_like(x, device=dev_from_str(dev))


def full(shape, fill_value, dtype=None, device=None):
    return _torch.full(
        ivy.shape_to_tuple(shape), fill_value, dtype=dtype_from_str(default_dtype(dtype, fill_value)),
        device=default_device(device))


# noinspection PyShadowingNames
def ones_like(x, dtype: Optional[str] = None, dev: Optional[str] = None):
    if dev is None:
        dev = _callable_dev(x)
    if dtype is not None:
        type_dict: Dict[str, _torch.dtype] = {'int8': _torch.int8,
            'int16': _torch.int16,
            'int32': _torch.int32,
            'int64': _torch.int64,
            'uint8': _torch.uint8,
            'bfloat16': _torch.bfloat16,
            'float16': _torch.float16,
            'float32': _torch.float32,
            'float64': _torch.float64,
            'bool': _torch.bool}
        return _torch.ones_like(x, dtype=type_dict[dtype], device=dev_from_str(dev))
    return _torch.ones_like(x, device=dev_from_str(dev))


# noinspection PyUnresolvedReferences,PyShadowingNames
def one_hot(indices, depth: int, dev: Optional[str] = None):
    if dev is None:
        dev = _callable_dev(indices)
    return _torch.nn.functional.one_hot(indices.type(_torch.int64), depth).to(dev_from_str(dev))


def cross(x1, x2):
    return _torch.cross(x1, x2)


def matmul(x1, x2):
    return _torch.matmul(x1, x2)


def cumsum(x, axis: int = 0):
    return _torch.cumsum(x, axis)


def cumprod(x, axis: int = 0, exclusive: bool = False):
    if exclusive:
        x = _torch.transpose(x, axis, -1)
        x = _torch.cat((_torch.ones_like(x[..., -1:]), x[..., :-1]), -1)
        res = _torch.cumprod(x, -1)
        return _torch.transpose(res, axis, -1)
    return _torch.cumprod(x, axis)


# noinspection PyShadowingNames
def identity(n: int, dtype: ivy.Dtype = 'float32', batch_shape: Optional[List[int]] = None,
             dev: Optional[str] = None):
    dev = default_device(dev)
    type_dict: Dict[str, _torch.dtype] = {'int8': _torch.int8,
            'int16': _torch.int16,
            'int32': _torch.int32,
            'int64': _torch.int64,
            'uint8': _torch.uint8,
            'bfloat16': _torch.bfloat16,
            'float16': _torch.float16,
            'float32': _torch.float32,
            'float64': _torch.float64,
            'bool': _torch.bool}
    dtype_val: _torch.dtype = type_dict[dtype]
    mat = _torch.eye(n, n, dtype=dtype_val, device=dev_from_str(dev))
    if batch_shape is None:
        return mat
    else:
        reshape_dims = [1] * len(batch_shape) + [n, n]
        tile_dims = list(batch_shape) + [1, 1]
        res = _torch.reshape(mat, reshape_dims).repeat(tile_dims)
        return res


def meshgrid(*xs, indexing='ij'):
    ret = _torch.meshgrid(*xs)
    if indexing == 'xy':
        # ToDo: verify if this is correct
        return tuple([_torch.transpose(x, 1, 0) for x in ret])
    return ret


# noinspection PyShadowingNames
def scatter_flat(indices, updates, size: Optional[int] = None, tensor: Optional[_torch.Tensor] = None,
                 reduction: str = 'sum', dev: Optional[str] = None):
    target = tensor
    target_given = ivy.exists(target)
    if ivy.exists(size) and ivy.exists(target):
        assert len(target.shape) == 1 and target.shape[0] == size
    if dev is None:
        dev = _callable_dev(updates)
    dtype = updates.dtype
    if reduction in ['sum', 'replace']:
        initial_val = _torch.tensor(0).type(dtype).to(dev_from_str(dev))
    elif reduction == 'min':
        initial_val = _torch.tensor(1e12).type(dtype).to(dev_from_str(dev))
    elif reduction == 'max':
        initial_val = _torch.tensor(-1e12).type(dtype).to(dev_from_str(dev))
    else:
        raise Exception('reduction is {}, but it must be one of "sum", "min" or "max"'.format(reduction))
    if target_given:
        output = tensor
    else:
        output = _torch.ones([size], dtype=dtype).to(dev_from_str(dev)) * initial_val
    global torch_scatter
    if torch_scatter is None:
        try:
            import torch_scatter as torch_scatter
        except:
            raise Exception('Unable to import torch_scatter, verify this is correctly installed.')
    if reduction == 'replace':
        output[indices.type(_torch.int64)] = updates
        res = output
    else:
        res = torch_scatter.scatter(updates, indices.type(_torch.int64), out=output, reduce=reduction)
    if not target_given:
        return _torch.where(res == initial_val, _torch.zeros([size], dtype=updates.dtype).to(dev_from_str(dev)), res)
    return res


# noinspection PyShadowingNames
def scatter_nd(indices, updates, shape=None, tensor=None, reduction='sum', dev=None):
    target = tensor
    target_given = ivy.exists(target)
    if ivy.exists(shape) and ivy.exists(target):
        assert ivy.shape_to_tuple(target.shape) == ivy.shape_to_tuple(shape)
    if dev is None:
        dev = _callable_dev(updates)
    shape = list(shape) if ivy.exists(shape) else list(tensor.shape)
    dtype = updates.dtype
    indices_shape = indices.shape
    num_index_dims = indices_shape[-1]
    result_dim_sizes_list = [_reduce(mul, shape[i + 1:], 1) for i in range(len(shape) - 1)] + [1]
    result_dim_sizes = _torch.tensor(result_dim_sizes_list).to(dev_from_str(dev))
    implicit_indices_factor = int(result_dim_sizes[num_index_dims - 1].item())
    flat_result_size = _reduce(mul, shape, 1)
    if reduction in ['sum', 'replace']:
        initial_val = _torch.tensor(0).type(dtype).to(dev_from_str(dev))
    elif reduction == 'min':
        initial_val = _torch.tensor(1e12).type(dtype).to(dev_from_str(dev))
    elif reduction == 'max':
        initial_val = _torch.tensor(-1e12).type(dtype).to(dev_from_str(dev))
    else:
        raise Exception('reduction is {}, but it must be one of "sum", "min" or "max"'.format(reduction))
    if target_given:
        flat_output = _torch.reshape(tensor, (flat_result_size,))
    else:
        flat_output = _torch.ones(flat_result_size, dtype=dtype).to(dev_from_str(dev)) * initial_val
    flat_updates = _torch.reshape(updates, (-1,))
    new_shape = [1] * (len(indices_shape) - 1) + [num_index_dims]
    indices_scales = _torch.reshape(result_dim_sizes[0:num_index_dims], new_shape)
    indices_for_flat_tiled = _torch.reshape(_torch.sum(indices * indices_scales, -1, keepdim=True), (-1, 1)).repeat(
        *[1, implicit_indices_factor])
    implicit_indices = _torch.unsqueeze(_torch.arange(implicit_indices_factor).to(dev_from_str(dev)), 0).repeat(
        *[indices_for_flat_tiled.shape[0], 1])
    indices_for_flat = indices_for_flat_tiled + implicit_indices
    flat_indices_for_flat = _torch.reshape(indices_for_flat, (-1,)).type(_torch.long)
    global torch_scatter
    if torch_scatter is None:
        try:
            import torch_scatter as torch_scatter
        except:
            raise Exception('Unable to import torch_scatter, verify this is correctly installed.')
    if reduction == 'replace':
        flat_output[flat_indices_for_flat] = flat_updates
        flat_scatter = flat_output
    else:
        flat_scatter = torch_scatter.scatter(flat_updates, flat_indices_for_flat, out=flat_output.clone(), reduce=reduction)
    if not target_given:
        # noinspection PyTypeChecker
        flat_scatter = _torch.where(flat_scatter == initial_val, _torch.zeros(flat_result_size, dtype=updates.dtype)
                                    .to(dev_from_str(dev)), flat_scatter)
    res = _torch.reshape(flat_scatter, list(shape))
    return res


# noinspection PyShadowingNames
def gather(params, indices, axis=-1, dev: Optional[str] = None):
    if dev is None:
        dev = _callable_dev(params)
    return _torch.gather(params, axis, indices.type(_torch.int64)).to(dev_from_str(dev))


# noinspection PyShadowingNames
def gather_nd(params, indices, dev: Optional[str] = None):
    if dev is None:
        dev = _callable_dev(params)
    indices_shape = indices.shape
    params_shape = params.shape
    num_index_dims = indices_shape[-1]
    result_dim_sizes_list = [_reduce(mul, params_shape[i + 1:], 1) for i in range(len(params_shape) - 1)] + [1]
    result_dim_sizes = _torch.tensor(result_dim_sizes_list).to(dev_from_str(dev))
    implicit_indices_factor = int(result_dim_sizes[num_index_dims - 1].item())
    flat_params = _torch.reshape(params, (-1,))
    new_shape = [1] * (len(indices_shape) - 1) + [num_index_dims]
    indices_scales = _torch.reshape(result_dim_sizes[0:num_index_dims], new_shape)
    indices_for_flat_tiled = _torch.reshape(_torch.sum(indices * indices_scales, -1, keepdim=True), (-1, 1)).repeat(
        *[1, implicit_indices_factor])
    implicit_indices = _torch.unsqueeze(_torch.arange(implicit_indices_factor).to(dev_from_str(dev)), 0).repeat(
        *[indices_for_flat_tiled.shape[0], 1])
    indices_for_flat = indices_for_flat_tiled + implicit_indices
    flat_indices_for_flat = _torch.reshape(indices_for_flat, (-1,)).type(_torch.long)
    flat_gather = _torch.gather(flat_params, 0, flat_indices_for_flat)
    res = _torch.reshape(flat_gather, list(indices_shape[:-1]) + list(params_shape[num_index_dims:]))
    return res


def linear_resample(x, num_samples: int, axis: int = -1):
    x_shape = list(x.shape)
    num_x_dims = len(x_shape)
    num_vals = x_shape[axis]
    axis = axis % num_x_dims
    if axis != num_x_dims - 1:
        x_pre_shape = x_shape[0:axis] + x_shape[-1:] + x_shape[axis + 1:-1]
        x = _torch.swapaxes(x, axis, -1)
    else:
        x_pre_shape = x_shape[:-1]
    x = _torch.reshape(x, ([-1, 1] + [num_vals]))
    ret = _torch.nn.functional.interpolate(x, num_samples, mode='linear', align_corners=True)
    ret = _torch.reshape(ret, x_pre_shape + [num_samples])
    if axis != num_x_dims - 1:
        return _torch.transpose(ret, -1, axis)
    return ret


def dtype(x, as_str=False):
    dt = x.dtype
    if as_str:
        return dtype_to_str(dt)
    return dt


def dtype_to_str(dtype_in):
    if isinstance(dtype_in, str):
        return dtype_in
    return {_torch.int8: 'int8',
            _torch.int16: 'int16',
            _torch.int32: 'int32',
            _torch.int64: 'int64',
            _torch.uint8: 'uint8',
            _torch.bfloat16: 'bfloat16',
            _torch.float16: 'float16',
            _torch.float32: 'float32',
            _torch.float64: 'float64',
            _torch.bool: 'bool'}[dtype_in]


def dtype_from_str(dtype_in: str) -> _torch.dtype:
    if not isinstance(dtype_in, str):
        return dtype_in
    return {'int8': _torch.int8,
            'int16': _torch.int16,
            'int32': _torch.int32,
            'int64': _torch.int64,
            'uint8': _torch.uint8,
            'bfloat16': _torch.bfloat16,
            'float16': _torch.float16,
            'float32': _torch.float32,
            'float64': _torch.float64,
            'bool': _torch.bool}[dtype_in]


def compile(fn, dynamic=True, example_inputs=None, static_argnums=None, static_argnames=None):
    if dynamic:
        return _torch.jit.script(fn)
    return _torch.jit.trace(fn, example_inputs)


def current_framework_str():
    return 'torch'


def multiprocessing(context=None):
    import torch.multiprocessing
    if context is None:
        return torch.multiprocessing
    return torch.multiprocessing.get_context(context)


def container_types():
    return []


def inplace_update(x, val):
    x.data = val
    return x


def inplace_decrement(x, val):
    x.data -= val
    return x


def inplace_increment(x, val):
    x.data += val
    return x


inplace_arrays_supported = lambda: True
inplace_variables_supported = lambda: True
