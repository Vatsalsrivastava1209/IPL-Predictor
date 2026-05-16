# IPL Predictor Backtest

Window: 2021-2024
Matches evaluated: 338

## Metrics
- Accuracy: 0.494
- Brier score: 0.260
- Log loss: 0.714
- Upset rate: 0.506

## Calibration
```text
 bucket  matches  avg_prediction  actual_win_rate
  0-20%        0             NaN              NaN
 20-40%       45        0.365581         0.355556
 40-60%      253        0.502507         0.537549
 60-80%       40        0.648427         0.325000
80-100%        0             NaN              NaN
```

## Notes
- This backtest evaluates match winner probabilities, not full-season champion odds.
- Retired teams are excluded so validation is aligned with the current-season simulator.
- The result should be used to compare model variants over time.