from contextlib import nullcontext

import torch
from PIL import Image
from transformers import DPTImageProcessor, DPTForDepthEstimation

from mgds.PipelineModule import PipelineModule
from mgds.pipelineModuleTypes.RandomAccessPipelineModule import RandomAccessPipelineModule


class GenerateDepth(
    PipelineModule,
    RandomAccessPipelineModule,
):
    def __init__(
            self,
            path_in_name: str,
            image_out_name: str,
            image_depth_processor: DPTImageProcessor,
            depth_estimator: DPTForDepthEstimation,
            autocast_context: torch.autocast | None = None,
    ):
        super(GenerateDepth, self).__init__()
        self.path_in_name = path_in_name
        self.image_out_name = image_out_name
        self.image_depth_processor = image_depth_processor
        self.depth_estimator = depth_estimator

        self.autocast_context = nullcontext() if autocast_context is None else autocast_context

    def length(self) -> int:
        return self._get_previous_length(self.path_in_name)

    def get_inputs(self) -> list[str]:
        return [self.path_in_name]

    def get_outputs(self) -> list[str]:
        return [self.image_out_name]

    def get_item(self, variation: int, index: int, requested_name: str = None) -> dict:
        path = self._get_previous_item(variation, self.path_in_name, index)

        try:
            image = Image.open(path)
        except:
            print("could not load image, it might be missing or corrupted: " + path)
            raise

        image = image.convert('RGB')

        with self.autocast_context:
            image = self.image_depth_processor(image, return_tensors="pt").pixel_values
            image = image.to(self.depth_estimator.dtype)
            depth = self.depth_estimator(image).predicted_depth

            depth_min = torch.amin(depth, dim=[1, 2], keepdim=True)
            depth_max = torch.amax(depth, dim=[1, 2], keepdim=True)
            depth = 2.0 * (depth - depth_min) / (depth_max - depth_min) - 1.0

        return {
            self.image_out_name: depth
        }
