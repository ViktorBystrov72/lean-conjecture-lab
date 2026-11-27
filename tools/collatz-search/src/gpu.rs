use anyhow::{Result, anyhow, ensure};
use metal::{CommandQueue, CompileOptions, ComputePipelineState, Device, MTLCommandBufferStatus};
use metal::{MTLResourceOptions, MTLSize};
use objc::rc::autoreleasepool;
use rayon::prelude::*;
use std::{ffi::c_void, mem::size_of_val, slice};

use crate::descent::{Window, descends, push_pending};

const LANES_PER_DISPATCH: u64 = 1 << 20;

pub struct Gpu {
    device: Device,
    queue: CommandQueue,
    pipeline: ComputePipelineState,
}

impl Gpu {
    pub fn new() -> Result<Self> {
        autoreleasepool(|| {
            let device = Device::system_default().ok_or_else(|| anyhow!("no Metal device"))?;
            let options = CompileOptions::new();
            let library = device
                .new_library_with_source(include_str!("descent.metal"), &options)
                .map_err(|e| anyhow!("Metal shader compilation: {e}"))?;
            let function = library
                .get_function("descent", None)
                .map_err(|e| anyhow!("Metal function: {e}"))?;
            let pipeline = device
                .new_compute_pipeline_state_with_function(&function)
                .map_err(|e| anyhow!("Metal pipeline: {e}"))?;
            let queue = device.new_command_queue();
            Ok(Self {
                device,
                queue,
                pipeline,
            })
        })
    }

    pub fn name(&self) -> &str {
        self.device.name()
    }

    pub fn scan(
        &self,
        window: Window<'_>,
        steps: u32,
        pool: &rayon::ThreadPool,
    ) -> Result<(Vec<u128>, u64)> {
        let slots = window.slots();
        if slots.is_empty() {
            return Ok((Vec::new(), 0));
        }
        let mode = MTLResourceOptions::StorageModeShared;
        let residues = self.device.new_buffer_with_data(
            window.residues.as_ptr().cast(),
            size_of_val(window.residues) as u64,
            mode,
        );
        let flags = self.device.new_buffer(LANES_PER_DISPATCH, mode);
        let group_size = (4 * self.pipeline.thread_execution_width())
            .min(self.pipeline.max_total_threads_per_threadgroup());
        let mut fallback = 0;
        let mut pending = Vec::new();
        for first in slots.clone().step_by(LANES_PER_DISPATCH as usize) {
            autoreleasepool(|| -> Result<()> {
                let len = (slots.end - first).min(LANES_PER_DISPATCH);
                let pointer = flags.contents().cast::<u8>();
                ensure!(
                    !pointer.is_null(),
                    "could not allocate a Metal result buffer"
                );
                // Shared storage is accessed by the host only outside command execution.
                unsafe { pointer.write_bytes(0, len as usize) };
                let residue_count = window.residues.len() as u64;
                let params: [u64; 7] = [
                    window.base as u64,
                    (window.base >> 64) as u64,
                    first / residue_count,
                    first % residue_count,
                    u64::from(window.bits),
                    residue_count,
                    u64::from(steps),
                ];
                let buffer = self.queue.new_command_buffer();
                let encoder = buffer.new_compute_command_encoder();
                encoder.set_compute_pipeline_state(&self.pipeline);
                encoder.set_buffer(0, Some(&residues), 0);
                encoder.set_buffer(1, Some(&flags), 0);
                encoder.set_bytes(
                    2,
                    size_of_val(&params) as u64,
                    params.as_ptr().cast::<c_void>(),
                );
                encoder.dispatch_threads(MTLSize::new(len, 1, 1), MTLSize::new(group_size, 1, 1));
                encoder.end_encoding();
                buffer.commit();
                buffer.wait_until_completed();
                ensure!(
                    buffer.status() == MTLCommandBufferStatus::Completed,
                    "Metal command did not complete: {:?}",
                    buffer.status()
                );
                let results = unsafe { slice::from_raw_parts(pointer, len as usize) };
                let mut replay = Vec::new();
                for (index, result) in results.iter().enumerate() {
                    match result {
                        1 => {}
                        2 => replay.push(window.at(first + index as u64)),
                        code => anyhow::bail!(
                            "invalid Metal status {code} at slot {}",
                            first + index as u64
                        ),
                    }
                }
                fallback += replay.len() as u64;
                let unresolved: Vec<_> = pool.install(|| {
                    replay
                        .into_par_iter()
                        .filter(|&n| !descends(n, steps))
                        .collect()
                });
                for n in unresolved {
                    push_pending(&mut pending, n)?;
                }
                Ok(())
            })?;
        }
        Ok((pending, fallback))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::descent::Sieve;

    #[test]
    #[ignore = "requires a Metal device"]
    fn matches_cpu_on_edges_overflow_and_partial_dispatches() {
        let gpu = Gpu::new().unwrap();
        let pool = rayon::ThreadPoolBuilder::new().build().unwrap();
        let sieve = Sieve::new(10).unwrap();
        let direct = Sieve::new(0).unwrap();
        let cases = [
            (sieve.window(251, 271).unwrap(), 9),
            (sieve.window((1 << 71) + 1, (1 << 71) + 41_337).unwrap(), 50),
            (direct.window(u128::MAX - 1_023, u128::MAX).unwrap(), 192),
            (
                sieve
                    .window((1 << 71) + 17, (1 << 71) + (1 << 24) + 31)
                    .unwrap(),
                10_000,
            ),
        ];
        for (window, budget) in cases {
            let (mut got, fallback) = gpu.scan(window, budget, &pool).unwrap();
            let mut expected = window.scan_cpu(budget).unwrap();
            assert!(fallback >= got.len() as u64);
            if window.base > u128::MAX - 2_000 {
                assert!(fallback > 0);
            }
            got.sort_unstable();
            expected.sort_unstable();
            assert_eq!(got, expected);
        }
    }
}
