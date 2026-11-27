use serde_json::Value;
use std::collections::BTreeSet;
use std::path::PathBuf;
use std::process::{Command, Output, Stdio};

struct StateDir(PathBuf);

impl StateDir {
    fn command(&self, action: &str, args: &[&str]) -> Command {
        let mut command = Command::new(env!("CARGO_BIN_EXE_collatz-search"));
        command.arg(action).arg("--state").arg(&self.0).args(args);
        command
    }

    fn run(&self, action: &str, args: &[&str]) -> Vec<Value> {
        decode(self.command(action, args).output().unwrap())
    }

    fn frontier(&self) -> String {
        self.run("status", &[])[0]["verified_below_given_base"]
            .as_str()
            .unwrap()
            .to_owned()
    }
}

impl Drop for StateDir {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

fn decode(output: Output) -> Vec<Value> {
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    String::from_utf8(output.stdout)
        .unwrap()
        .lines()
        .map(|line| serde_json::from_str(line).unwrap())
        .collect()
}

#[test]
fn workers_resume_without_overlaps_or_claiming_across_gaps() {
    let state = StateDir(
        PathBuf::from(env!("CARGO_TARGET_TMPDIR")).join(format!("queue-{}", std::process::id())),
    );
    state.run(
        "init",
        &[
            "--known-below",
            "32",
            "--first-exp",
            "5",
            "--last-exp",
            "6",
            "--block-bits",
            "3",
            "--sieve-bits",
            "0",
            "--steps",
            "1",
        ],
    );
    state.run("work", &["--lane", "6", "--threads", "1"]);
    assert_eq!(state.frontier(), "32");
    let coverage = state.command("coverage", &["--save"]).output().unwrap();
    assert!(coverage.status.success());
    let report = std::fs::read_to_string(state.0.join("coverage.md")).unwrap();
    assert_eq!(coverage.stdout, report.as_bytes());
    assert!(report.contains("**Contiguous convergence given the configured base** `[1, 32)`"));
    assert!(report.contains("| 6 | `[64, 65)` | `[64, 72)` | 4 | `65` | 1 |"));

    let children: Vec<_> = ["alpha", "beta", "gamma"]
        .into_iter()
        .map(|name| {
            state
                .command("work", &["--lane", "5", "--threads", "1", "--worker", name])
                .stdout(Stdio::piped())
                .stderr(Stdio::piped())
                .spawn()
                .unwrap()
        })
        .collect();
    let mut checked = BTreeSet::new();
    for child in children {
        let report = decode(child.wait_with_output().unwrap());
        if let Some(from) = report[0]["block"]["from"].as_str() {
            assert!(checked.insert(from.to_owned()));
        }
    }
    assert!(checked.contains("32"));
    assert_eq!(state.frontier(), "33");

    state.run("work", &["--lane", "5", "--blocks", "4", "--threads", "1"]);
    state.run(
        "trace-work",
        &["--lane", "5", "--steps", "1000", "--limit", "64"],
    );
    assert_eq!(state.frontier(), "65");
    state.run(
        "trace-work",
        &["--lane", "6", "--steps", "1000", "--limit", "64"],
    );
    assert_eq!(state.frontier(), "72");
    let coverage = state.command("coverage", &["--save"]).output().unwrap();
    assert!(coverage.status.success());
    let report = std::fs::read_to_string(state.0.join("coverage.md")).unwrap();
    assert!(report.contains("**Contiguous convergence given the configured base** `[1, 72)`"));
    assert!(report.contains("| 6 | `[64, 72)` | `[64, 72)` | 0 | — | 1 |"));

    state.run("cycle-work", &["--odd-exp", "5"]);
    let a = state.run(
        "word-work",
        &["--length", "8", "--prefix-bits", "2", "--shard", "0"],
    );
    let b = state.run(
        "word-work",
        &["--length", "8", "--prefix-bits", "2", "--shard", "1"],
    );
    assert_eq!(a[0]["prefix"], "00");
    assert_eq!(b[0]["prefix"], "01");
    assert!(
        !state
            .command(
                "word-work",
                &["--length", "8", "--prefix-bits", "3", "--shard", "3"]
            )
            .output()
            .unwrap()
            .status
            .success()
    );
    let status = state.run("status", &[]);
    assert_eq!(status[0]["cycle_screens"].as_array().unwrap().len(), 1);
    assert_eq!(status[0]["parity_batches"].as_array().unwrap().len(), 2);
}

#[test]
fn target_clips_blocks_and_waits_for_unresolved_starts() {
    let state = StateDir(
        PathBuf::from(env!("CARGO_TARGET_TMPDIR")).join(format!("goal-{}", std::process::id())),
    );
    state.run(
        "init",
        &[
            "--known-below",
            "32",
            "--first-exp",
            "5",
            "--last-exp",
            "6",
            "--block-bits",
            "3",
            "--sieve-bits",
            "0",
            "--steps",
            "1",
            "--target-below",
            "43",
        ],
    );
    let blocks = state.run("work", &["--blocks", "8", "--threads", "1"]);
    assert_eq!(blocks.len(), 2);
    assert_eq!(blocks[0]["block"]["to_exclusive"], "40");
    assert_eq!(blocks[1]["block"]["to_exclusive"], "43");
    let status = state.run("status", &[]);
    assert_eq!(status[0]["goal"]["scanned"], true);
    assert_eq!(status[0]["goal"]["reached"], false);
    assert_eq!(status[0]["verified_below_given_base"], "33");
    assert_eq!(
        state.run("work", &["--lane", "6"])[0]["status"],
        "no_claimable_lane"
    );

    // Emulate interruption after the checkpoint was saved and before it was archived.
    let missing = state.0.join("lane-5/journal/00000000000000000002.json");
    std::fs::remove_file(&missing).unwrap();
    let history = state.run("history", &["--limit", "2"]);
    assert_eq!(history[0]["events"][1]["details"]["to_exclusive"], "43");
    let trace = state.run("trace-work", &["--steps", "1000", "--limit", "64"]);
    assert_eq!(trace.last().unwrap()["status"], "goal_reached");
    assert!(missing.is_file());
    assert_eq!(state.frontier(), "43");
    assert_eq!(state.run("work", &[])[0]["status"], "goal_reached");
    assert_eq!(
        state.run("history", &["--lane", "5", "--limit", "1"])[0]["events"][0]["stage"],
        "trace_finished"
    );

    state.run("set-target", &["--target-below", "46"]);
    let next = state.run("work", &["--blocks", "8", "--threads", "1"]);
    assert_eq!(next[0]["block"]["from"], "43");
    assert_eq!(next[0]["block"]["to_exclusive"], "46");
}
