# -*- coding: utf-8 -*-
import math
from typing import List

import numpy as np

import megengine as mge
import megengine.functional as F
import megengine.module as M
from megengine import Tensor
from megengine.module.normalization import GroupNorm

from official.vision.detection import layers


class PointHead(M.Module):
    """
    The head used when anchor points are adopted for object classification and box regression.
    """

    def __init__(self, cfg, input_shape: List[layers.ShapeSpec]):
        super().__init__()
        self.stride_list = cfg.stride

        in_channels = input_shape[0].channels
        num_classes = cfg.num_classes
        num_convs = 4
        prior_prob = cfg.cls_prior_prob
        num_anchors = [cfg.num_anchors] * len(input_shape)

        assert (
            len(set(num_anchors)) == 1
        ), "not support different number of anchors between levels"
        num_anchors = num_anchors[0]

        cls_subnet = []
        bbox_subnet = []
        for _ in range(num_convs):
            cls_subnet.append(
                M.Conv2d(in_channels, in_channels, kernel_size=3, stride=1, padding=1)
            )
            cls_subnet.append(GroupNorm(32, in_channels))
            cls_subnet.append(M.ReLU())
            bbox_subnet.append(
                M.Conv2d(in_channels, in_channels, kernel_size=3, stride=1, padding=1)
            )
            bbox_subnet.append(GroupNorm(32, in_channels))
            bbox_subnet.append(M.ReLU())

        self.cls_subnet = M.Sequential(*cls_subnet)
        self.bbox_subnet = M.Sequential(*bbox_subnet)
        self.cls_score = M.Conv2d(
            in_channels, num_anchors * num_classes, kernel_size=3, stride=1, padding=1
        )
        self.bbox_pred = M.Conv2d(
            in_channels, num_anchors * 4, kernel_size=3, stride=1, padding=1
        )
        self.ctrness = M.Conv2d(
            in_channels, num_anchors * 1, kernel_size=3, stride=1, padding=1
        )

        # Initialization
        for modules in [
            self.cls_subnet, self.bbox_subnet, self.cls_score, self.bbox_pred,
            self.ctrness
        ]:
            for layer in modules.modules():
                if isinstance(layer, M.Conv2d):
                    M.init.normal_(layer.weight, mean=0, std=0.01)
                    M.init.fill_(layer.bias, 0)

        # Use prior in model initialization to improve stability
        bias_value = -math.log((1 - prior_prob) / prior_prob)
        M.init.fill_(self.cls_score.bias, bias_value)

        self.scale_list = mge.Parameter(np.ones(len(self.stride_list), dtype=np.float32))

    def forward(self, features: List[Tensor]):
        logits, offsets, ctrness = [], [], []
        for feature, scale, stride in zip(features, self.scale_list, self.stride_list):
            logits.append(self.cls_score(self.cls_subnet(feature)))
            bbox_subnet = self.bbox_subnet(feature)
            offsets.append(F.relu(self.bbox_pred(bbox_subnet) * scale) * stride)
            ctrness.append(self.ctrness(bbox_subnet))
        return logits, offsets, ctrness