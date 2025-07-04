# SPDX-FileCopyrightText: © 2024 Tenstorrent Inc.

# SPDX-License-Identifier: Apache-2.0

import time

import pytest
import torch
from loguru import logger

import ttnn
from models.demos.yolov4.runner.performant_runner import YOLOv4PerformantRunner
from models.perf.perf_utils import prep_perf_report
from models.utility_functions import run_for_wormhole_b0


@run_for_wormhole_b0()
@pytest.mark.models_performance_bare_metal
@pytest.mark.parametrize(
    "device_params", [{"l1_small_size": 40960, "trace_region_size": 6434816, "num_command_queues": 2}], indirect=True
)
@pytest.mark.parametrize(
    "batch_size, act_dtype, weight_dtype",
    ((1, ttnn.bfloat16, ttnn.bfloat16),),
)
@pytest.mark.parametrize(
    "resolution, expected_inference_throughput",
    [((320, 320), 103), ((640, 640), 46)],
)
def test_e2e_performant(device, batch_size, act_dtype, weight_dtype, resolution, expected_inference_throughput):
    performant_runner = YOLOv4PerformantRunner(
        device,
        batch_size,
        act_dtype,
        weight_dtype,
        resolution=resolution,
        model_location_generator=None,
    )
    inference_times = []
    for _ in range(10):
        input_shape = (1, 3, *resolution)
        torch_input_tensor = torch.randn(input_shape, dtype=torch.float32)

        t0 = time.time()
        _ = performant_runner.run(torch_input_tensor)
        t1 = time.time()
        inference_times.append(t1 - t0)

    performant_runner.release()

    inference_time_avg = round(sum(inference_times) / len(inference_times), 6)
    logger.info(
        f"average inference time (ms): {inference_time_avg * 1000}, average throughput (fps): {round(batch_size/inference_time_avg)}"
    )

    expected_inference_time = batch_size / expected_inference_throughput
    prep_perf_report(
        model_name="yolov4",
        batch_size=batch_size,
        inference_and_compile_time=inference_time_avg,
        inference_time=inference_time_avg,
        expected_compile_time=1,
        expected_inference_time=expected_inference_time,
        comments="",
        inference_time_cpu=0.0,
    )
