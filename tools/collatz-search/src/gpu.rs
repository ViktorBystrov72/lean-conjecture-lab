use anyhow::{Context, Result, anyhow, ensure};
use metal::{
    Buffer, CommandBuffer, CommandQueue, CompileOptions, ComputePipelineState, Device,
    MTLCommandBufferStatus, MTLResourceOptions, MTLSize,
};
use objc::rc::autoreleasepool;
use rayon::prelude::*;
use std::{ffi::c_void, mem::size_of_val, ops::Range, slice};

use crate::descent::{Window, descends, push_pending};

const LANES_PER_DISPATCH: u64 = 1 << 20;

pub struct Gpu {
    device: Device,
    queue: CommandQueue,
    pipeline: ComputePipelineState,
    group_size: u64,
}

struct ResultBuffer {
    flags: Buffer,
    dispatch: Option<(CommandBuffer, Range<u64>)>,
}

impl ResultBuffer {
    fn new(flags: Buffer) -> Self {
        Self {
            flags,
            dispatch: None,
        }
    }

    fn results(&mut self) -> Result<(u64, &[u8])> {
        let (command, slots) = self.dispatch.take().context("no Metal command submitted")?;
        command.wait_until_completed();
        let status = command.status();
        ensure!(
            status == MTLCommandBufferStatus::Completed,
            "Metal command did not complete: {status:?}"
        );
        let len = (slots.end - slots.start) as usize;
        // This buffer is initialized during submission and the GPU has finished writing it.
        let results = unsafe { slice::from_raw_parts(self.flags.contents().cast::<u8>(), len) };
        Ok((slots.start, results))
    }
}

impl Drop for ResultBuffer {
    fn drop(&mut self) {
        // Drain any queued command if processing the other buffer returned an error.
        if let Some((command, _)) = &self.dispatch {
            command.wait_until_completed();
        }
    }
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
            let group_size = (4 * pipeline.thread_execution_width())
                .min(pipeline.max_total_threads_per_threadgroup());
            let queue = device.new_command_queue();
            Ok(Self {
                device,
                queue,
                pipeline,
                group_size,
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
        let mut dispatches = slots
            .clone()
            .step_by(LANES_PER_DISPATCH as usize)
            .map(|first| first..slots.end.min(first + LANES_PER_DISPATCH));
        let Some(first) = dispatches.next() else {
            return Ok((Vec::new(), 0));
        };
        let mode = MTLResourceOptions::StorageModeShared;
        let residues = self.device.new_buffer_with_data(
            window.residues.as_ptr().cast(),
            size_of_val(window.residues) as u64,
            mode,
        );
        let new_buffer = || ResultBuffer::new(self.device.new_buffer(LANES_PER_DISPATCH, mode));
        let mut current = new_buffer();
        let mut next = new_buffer();
        let mut fallback = 0;
        let mut pending = Vec::new();
        let mut collect_results = |buffer: &mut ResultBuffer| -> Result<()> {
            let (first, results) = buffer.results()?;
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
        };
        self.submit(window, steps, &residues, &mut current, first)?;
        for slots in dispatches {
            // Submit to the other buffer before waiting for and reading the current one.
            self.submit(window, steps, &residues, &mut next, slots)?;
            collect_results(&mut current)?;
            std::mem::swap(&mut current, &mut next);
        }
        collect_results(&mut current)?;
        Ok((pending, fallback))
    }

    fn submit(
        &self,
        window: Window<'_>,
        steps: u32,
        residues: &Buffer,
        result_buffer: &mut ResultBuffer,
        slots: Range<u64>,
    ) -> Result<()> {
        ensure!(
            result_buffer.dispatch.is_none(),
            "Metal result buffer is still in use"
        );
        let len = slots.end - slots.start;
        let pointer = result_buffer.flags.contents().cast::<u8>();
        ensure!(
            !pointer.is_null(),
            "could not allocate a Metal result buffer"
        );
        // The CPU can initialize this buffer while the GPU writes to the other one.
        unsafe { pointer.write_bytes(0, len as usize) };
        let residue_count = window.residues.len() as u64;
        let params: [u64; 7] = [
            window.base as u64,
            (window.base >> 64) as u64,
            slots.start / residue_count,
            slots.start % residue_count,
            u64::from(window.bits),
            residue_count,
            u64::from(steps),
        ];
        let command = autoreleasepool(|| {
            let command = self.queue.new_command_buffer().to_owned();
            let encoder = command.new_compute_command_encoder();
            encoder.set_compute_pipeline_state(&self.pipeline);
            encoder.set_buffer(0, Some(residues), 0);
            encoder.set_buffer(1, Some(&result_buffer.flags), 0);
            encoder.set_bytes(
                2,
                size_of_val(&params) as u64,
                params.as_ptr().cast::<c_void>(),
            );
            encoder.dispatch_threads(MTLSize::new(len, 1, 1), MTLSize::new(self.group_size, 1, 1));
            encoder.end_encoding();
            command.commit();
            command
        });
        result_buffer.dispatch = Some((command, slots));
        Ok(())
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

    #[test]
    #[ignore = "requires a Metal device"]
    fn matches_cpu_when_reusing_a_result_buffer() {
        let gpu = Gpu::new().unwrap();
        let pool = rayon::ThreadPoolBuilder::new().build().unwrap();
        let sieve = Sieve::new(10).unwrap();
        let base = 1 << 71;
        let window = sieve
            .window(base + 17, base + (1 << 25) + (1 << 19) + 31)
            .unwrap();
        let candidates = window.candidates();
        assert!(candidates > 2 * LANES_PER_DISPATCH && candidates < 3 * LANES_PER_DISPATCH);

        let budget = 96;
        let (mut got, fallback) = gpu.scan(window, budget, &pool).unwrap();
        let mut expected = window.scan_cpu(budget).unwrap();
        assert!(!expected.is_empty());
        assert_eq!(fallback, expected.len() as u64);
        got.sort_unstable();
        expected.sort_unstable();
        assert_eq!(got, expected);
    }
}
