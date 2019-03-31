from __future__ import absolute_import
import six
import importlib
from .config_exceptions import BadConfig
import os
import sys
import logging
logger = logging.getLogger(__name__)


__all__ = ["sequence_from_dict"]


class BadStagesDescription(BadConfig):
    pass


class BadStageList(BadConfig):
    pass


def sequence_from_dict(stages, general={}, **stage_descriptions):
    output_dir = general.get("output_dir", os.getcwd())
    default_module = general.get("backend", None)
    if default_module:
        default_module = importlib.import_module(default_module)
    stages = _create_stages(stages, output_dir, stage_descriptions, default_module=default_module)
    return stages


def _create_stages(stages, output_dir, stage_descriptions, default_module=None):
    if not isinstance(stages, list):
        msg = "Bad stage list: Should be a list"
        logger.error(msg + ", but instead got a '{}'".format(type(stages)))
        raise BadStageList(msg)
    out_stages = []
    for i, stage_cfg in enumerate(stages):
        name, stage_type = infer_stage_name_class(i, stage_cfg, default_module=default_module)
        # out_stages = instantiate_stage(name, stage_class, default_module, output_dir, stage_descriptions)
        stage_class = get_stage_class(stage_type, default_module, raise_exception=False)
        if not stage_class:
            raise BadStagesDescription("Unknown type for stage '{}': {}".format(name, stage_type))
        out_stages += _configure_stage(name, stage_class, output_dir, stage_descriptions)
    return out_stages


def _configure_stage(name, stage_class, out_dir, stage_descriptions):
    cfg = stage_descriptions.get(name, None)
    if cfg is None:
        raise BadStagesDescription("Missing description for stage '{}'".format(name))
    if isinstance(cfg, dict):
        cfg.setdefault("name", name)
        cfg.setdefault("out_dir", out_dir)
        stage = stage_class(**cfg)
    elif isinstance(cfg, list):
        stage = stage_class(*cfg)
    else:
        stage = stage_class(cfg, name=name)
    return [stage]


def infer_stage_name_class(index, stage_cfg, default_type="BinnedDataframe", default_module=None):
    if not isinstance(stage_cfg, dict):
        msg = "Bad stage configuration, for stage {} in stages list".format(index)
        logger.error(msg + ". Each stage config must be a dictionary with single key")
        raise BadStagesDescription(msg)
    if len(stage_cfg) != 1:
        msg = "More than one key in dictionary spec for stage {} in stages list".format(index)
        logger.error(msg + "\n dictionary given: {}".format(stage_cfg))
        raise BadStagesDescription(msg)
    [(name, stage_type)] = stage_cfg.items()
    if not isinstance(stage_type, six.string_types):
        msg = "Type of stage {} in stages list should be specified as a string".format(index)
        logger.error(msg + "\n Stage Type provided: {}".format(stage_type))
        raise BadStagesDescription(msg)
    return name, stage_type


def get_stage_class(class_name, default_module, raise_exception=True):
    if not default_module:
        default_module = sys.modules[__name__]

    if "." not in class_name:
        module = default_module
    else:
        path = class_name.split(".")
        mod_name = ".".join(path[:-1])
        class_name = path[-1]
        module = importlib.import_module(mod_name)
    actual_class = getattr(module, class_name, None)
    if not actual_class and raise_exception:
        raise RuntimeError("Unknown manip class, '{}'".format(class_name))
    return actual_class
