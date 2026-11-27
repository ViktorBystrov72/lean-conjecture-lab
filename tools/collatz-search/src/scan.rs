use anyhow::{Result, ensure};
use clap::ValueEnum;
use rayon::{ThreadPool, ThreadPoolBuilder};
use std::time::Instant;

use crate::descent::{Block, Sieve};
#[cfg(target_os = "macos")]
use crate::gpu::Gpu;

#[derive(Clone, Copy, Debug, ValueEnum)]
pub enum Backend {
    Cpu,
    Metal,
}

impl Backend {
    pub fn label(self) -> &'static str {
        match self {
            Self::Cpu => "cpu",
            Self::Metal => "metal",
        }
    }
}

pub struct Scan {
    pool: ThreadPool,
    sieve: Sieve,
    #[cfg(target_os = "macos")]
    gpu: Option<Gpu>,
}

impl Scan {
    pub fn new(backend: Backend, threads: usize, bits: u32, steps: u32) -> Result<Self> {
        ensure!(steps > 0, "step budget must be positive");
        let pool = ThreadPoolBuilder::new().num_threads(threads).build()?;
        let sieve = pool.install(|| Sieve::new(bits.min(steps)))?;
        #[cfg(not(target_os = "macos"))]
        ensure!(matches!(backend, Backend::Cpu), "Metal requires macOS");
        #[cfg(target_os = "macos")]
        let gpu = match backend {
            Backend::Cpu => None,
            Backend::Metal => {
                let gpu = Gpu::new()?;
                eprintln!("Metal device: {}", gpu.name());
                Some(gpu)
            }
        };
        Ok(Self {
            pool,
            sieve,
            #[cfg(target_os = "macos")]
            gpu,
        })
    }

    pub fn block(&self, start: u128, stop: u128, steps: u32) -> Result<(Block, f64)> {
        let began = Instant::now();
        let window = self.sieve.window(start, stop)?;
        // The Metal objects stay on the calling thread. Only CPU work is sent to Rayon.
        let cpu_result = || {
            self.pool
                .install(|| window.scan_cpu(steps))
                .map(|ns| (ns, 0))
        };
        #[cfg(target_os = "macos")]
        let result = match &self.gpu {
            Some(gpu) => gpu.scan(window, steps, &self.pool),
            None => cpu_result(),
        };
        #[cfg(not(target_os = "macos"))]
        let result = cpu_result();
        let (mut unresolved, exact_replays) = result?;
        unresolved.sort_unstable();
        let orbit_checks = window.candidates();
        Ok((
            Block {
                from: start.to_string(),
                to_exclusive: stop.to_string(),
                sieved: (stop - start) as u64 - orbit_checks,
                orbit_checks,
                exact_replays,
                unresolved: unresolved.iter().map(u128::to_string).collect(),
            },
            began.elapsed().as_secs_f64(),
        ))
    }
}
