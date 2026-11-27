use std::str::FromStr;

use anyhow::{Result, ensure};
use num_bigint::BigUint;
use num_traits::One;
use serde::Serialize;

use crate::descent::shortcut_big;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Outcome {
    ReachesOne,
    Descended,
    Cycle,
    StepLimit,
}

#[derive(Debug, Serialize)]
pub struct Trace {
    pub n: String,
    pub outcome: Outcome,
    pub steps: u64,
    pub last: String,
    pub maximum: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub period: Option<u64>,
}

pub fn trace(input: &str, limit: u64, until_one: bool) -> Result<Trace> {
    let n = BigUint::from_str(input)?;
    ensure!(
        n > BigUint::ZERO && limit > 0,
        "start and step budget must be positive"
    );
    let mut x = n.clone();
    let mut max = n.clone();
    let mut anchor = n.clone();
    let mut power = 1u64;
    let mut distance = 0;
    let report = |outcome, steps, last: &BigUint, maximum: &BigUint, period| Trace {
        n: n.to_string(),
        outcome,
        steps,
        last: last.to_string(),
        maximum: maximum.to_string(),
        period,
    };
    if n.is_one() {
        return Ok(report(Outcome::ReachesOne, 0, &n, &n, None));
    }
    for steps in 1..=limit {
        shortcut_big(&mut x);
        if x > max {
            max.clone_from(&x);
        }
        if x.is_one() {
            return Ok(report(Outcome::ReachesOne, steps, &x, &max, None));
        }
        if !until_one && x < n {
            return Ok(report(Outcome::Descended, steps, &x, &max, None));
        }
        // Brent's cycle detection keeps a single checkpoint and the current value.
        distance += 1;
        if x == anchor {
            return Ok(report(Outcome::Cycle, steps, &x, &max, Some(distance)));
        }
        if distance == power {
            anchor.clone_from(&x);
            distance = 0;
            power = power.saturating_mul(2);
        }
    }
    Ok(report(Outcome::StepLimit, limit, &x, &max, None))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn limit_descent_and_reaches_one_are_distinct() {
        assert_eq!(trace("27", 5, false).unwrap().outcome, Outcome::StepLimit);
        assert_eq!(trace("27", 100, false).unwrap().outcome, Outcome::Descended);
        assert_eq!(trace("27", 111, true).unwrap().outcome, Outcome::ReachesOne);
    }
}
