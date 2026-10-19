# Acceptance, uncertainty and failure distributions

Fresh final32worlds/condition. All rates include counts and Wilson95% intervals. Reused seeds across conditions are not independent campaigns. Accepted=source weight≥.9, region<half domain, no predictive or comparison mismatch. Abstained=fit but not accepted; refusals are separate. Wrong means the primary simulated source is outside the conditional region. A covered region can still have a distant MAP. Background-only has no geographic truth; source-family false alarms are separate.

| Condition | Model | Acceptance/all generated [95%] | Wrong/accepted [95%] | Wrong/generated [95%] | Coverage/fitted [95%] |
|---|---|---|---|---|---|
|characterized_nominal|baseline-0.4.0|11/32; 34.4% [20.4,51.7]|0/11; 0.0% [0.0,25.9]|0/32; 0.0% [0.0,10.7]|32/32; 100.0% [89.3,100.0]|
|characterized_nominal|plume-weather-0.5.0|11/32; 34.4% [20.4,51.7]|0/11; 0.0% [0.0,25.9]|0/32; 0.0% [0.0,10.7]|32/32; 100.0% [89.3,100.0]|
|unknown_nominal|baseline-0.4.0|11/32; 34.4% [20.4,51.7]|0/11; 0.0% [0.0,25.9]|0/32; 0.0% [0.0,10.7]|32/32; 100.0% [89.3,100.0]|
|unknown_nominal|plume-weather-0.5.0|8/32; 25.0% [13.3,42.1]|0/8; 0.0% [0.0,32.4]|0/32; 0.0% [0.0,10.7]|32/32; 100.0% [89.3,100.0]|
|direction_unknown|baseline-0.4.0|7/32; 21.9% [11.0,38.8]|7/7; 100.0% [64.6,100.0]|7/32; 21.9% [11.0,38.8]|10/32; 31.2% [18.0,48.6]|
|direction_unknown|plume-weather-0.5.0|9/32; 28.1% [15.6,45.4]|0/9; 0.0% [0.0,29.9]|0/32; 0.0% [0.0,10.7]|30/32; 93.8% [79.9,98.3]|
|direction_characterized|baseline-0.4.0|7/32; 21.9% [11.0,38.8]|7/7; 100.0% [64.6,100.0]|7/32; 21.9% [11.0,38.8]|10/32; 31.2% [18.0,48.6]|
|direction_characterized|plume-weather-0.5.0|10/32; 31.2% [18.0,48.6]|0/10; 0.0% [0.0,27.8]|0/32; 0.0% [0.0,10.7]|31/32; 96.9% [84.3,99.4]|
|speed_bias|baseline-0.4.0|10/32; 31.2% [18.0,48.6]|0/10; 0.0% [0.0,27.8]|0/32; 0.0% [0.0,10.7]|32/32; 100.0% [89.3,100.0]|
|speed_bias|plume-weather-0.5.0|6/32; 18.8% [8.9,35.3]|0/6; 0.0% [0.0,39.0]|0/32; 0.0% [0.0,10.7]|32/32; 100.0% [89.3,100.0]|
|clock_lag|baseline-0.4.0|4/32; 12.5% [5.0,28.1]|2/4; 50.0% [15.0,85.0]|2/32; 6.2% [1.7,20.1]|24/32; 75.0% [57.9,86.7]|
|clock_lag|plume-weather-0.5.0|3/32; 9.4% [3.2,24.2]|0/3; 0.0% [0.0,56.2]|0/32; 0.0% [0.0,10.7]|32/32; 100.0% [89.3,100.0]|
|distant_station|baseline-0.4.0|0/32; 0.0% [0.0,10.7]|0/0; undefined|0/32; 0.0% [0.0,10.7]|0/0; undefined|
|distant_station|plume-weather-0.5.0|0/32; 0.0% [0.0,10.7]|0/0; undefined|0/32; 0.0% [0.0,10.7]|0/0; undefined|
|spatial_winds|baseline-0.4.0|11/32; 34.4% [20.4,51.7]|10/11; 90.9% [62.3,98.4]|10/32; 31.2% [18.0,48.6]|16/32; 50.0% [33.6,66.4]|
|spatial_winds|plume-weather-0.5.0|10/32; 31.2% [18.0,48.6]|4/10; 40.0% [16.8,68.7]|4/32; 12.5% [5.0,28.1]|27/32; 84.4% [68.2,93.1]|
|variable_weather|baseline-0.4.0|0/32; 0.0% [0.0,10.7]|0/0; undefined|0/32; 0.0% [0.0,10.7]|0/0; undefined|
|variable_weather|plume-weather-0.5.0|0/32; 0.0% [0.0,10.7]|0/0; undefined|0/32; 0.0% [0.0,10.7]|0/0; undefined|
|weak|baseline-0.4.0|0/32; 0.0% [0.0,10.7]|0/0; undefined|0/32; 0.0% [0.0,10.7]|25/32; 78.1% [61.2,89.0]|
|weak|plume-weather-0.5.0|0/32; 0.0% [0.0,10.7]|0/0; undefined|0/32; 0.0% [0.0,10.7]|27/32; 84.4% [68.2,93.1]|
|correlated|baseline-0.4.0|5/32; 15.6% [6.9,31.8]|2/5; 40.0% [11.8,76.9]|2/32; 6.2% [1.7,20.1]|22/32; 68.8% [51.4,82.0]|
|correlated|plume-weather-0.5.0|5/32; 15.6% [6.9,31.8]|1/5; 20.0% [3.6,62.4]|1/32; 3.1% [0.6,15.7]|22/32; 68.8% [51.4,82.0]|
|two_sources|baseline-0.4.0|16/32; 50.0% [33.6,66.4]|5/16; 31.2% [14.2,55.6]|5/32; 15.6% [6.9,31.8]|25/32; 78.1% [61.2,89.0]|
|two_sources|plume-weather-0.5.0|13/32; 40.6% [25.5,57.7]|4/13; 30.8% [12.7,57.6]|4/32; 12.5% [5.0,28.1]|26/32; 81.2% [64.7,91.1]|
|background|baseline-0.4.0|0/32; 0.0% [0.0,10.7]|0/0; undefined|0/32; 0.0% [0.0,10.7]|0/0; undefined|
|background|plume-weather-0.5.0|0/32; 0.0% [0.0,10.7]|0/0; undefined|0/32; 0.0% [0.0,10.7]|0/0; undefined|
|independent_transport|baseline-0.4.0|13/32; 40.6% [25.5,57.7]|4/13; 30.8% [12.7,57.6]|4/32; 12.5% [5.0,28.1]|28/32; 87.5% [71.9,95.0]|
|independent_transport|plume-weather-0.5.0|13/32; 40.6% [25.5,57.7]|3/13; 23.1% [8.2,50.3]|3/32; 9.4% [3.2,24.2]|29/32; 90.6% [75.8,96.8]|

## Diagnostic false alarms and missed failures

The table records diagnostic mismatch screens, separate from the generic unknown-weather notice. No warning does not verify weather. Nominal characterized rows measure false warnings under compatible synthetic conditions. Unwarned geographic misses count covered=false even among abstentions. Unknown-direction/speed/clock/spatial errors can remain undetected; uncertainty integration is not a detector of physical bias. No false-positive/negative field calibration follows.

| Condition | Model | Predictive warning [95%] | Comparison warning [95%] | Unwarned region misses | Source presence miss [95%] | False source alarm [95%] |
|---|---|---|---|---|---|---|
|characterized_nominal|baseline-0.4.0|0/32; 0.0% [0.0,10.7]|0/32; 0.0% [0.0,10.7]|0|17/32; 53.1% [36.4,69.1]|0/0; undefined|
|characterized_nominal|plume-weather-0.5.0|0/32; 0.0% [0.0,10.7]|0/32; 0.0% [0.0,10.7]|0|16/32; 50.0% [33.6,66.4]|0/0; undefined|
|unknown_nominal|baseline-0.4.0|0/32; 0.0% [0.0,10.7]|0/32; 0.0% [0.0,10.7]|0|17/32; 53.1% [36.4,69.1]|0/0; undefined|
|unknown_nominal|plume-weather-0.5.0|0/32; 0.0% [0.0,10.7]|0/32; 0.0% [0.0,10.7]|0|18/32; 56.2% [39.3,71.8]|0/0; undefined|
|direction_unknown|baseline-0.4.0|2/32; 6.2% [1.7,20.1]|0/32; 0.0% [0.0,10.7]|20|18/32; 56.2% [39.3,71.8]|0/0; undefined|
|direction_unknown|plume-weather-0.5.0|1/32; 3.1% [0.6,15.7]|0/32; 0.0% [0.0,10.7]|1|17/32; 53.1% [36.4,69.1]|0/0; undefined|
|direction_characterized|baseline-0.4.0|2/32; 6.2% [1.7,20.1]|0/32; 0.0% [0.0,10.7]|20|18/32; 56.2% [39.3,71.8]|0/0; undefined|
|direction_characterized|plume-weather-0.5.0|1/32; 3.1% [0.6,15.7]|0/32; 0.0% [0.0,10.7]|0|13/32; 40.6% [25.5,57.7]|0/0; undefined|
|speed_bias|baseline-0.4.0|1/32; 3.1% [0.6,15.7]|0/32; 0.0% [0.0,10.7]|0|13/32; 40.6% [25.5,57.7]|0/0; undefined|
|speed_bias|plume-weather-0.5.0|1/32; 3.1% [0.6,15.7]|0/32; 0.0% [0.0,10.7]|0|14/32; 43.8% [28.2,60.7]|0/0; undefined|
|clock_lag|baseline-0.4.0|6/32; 18.8% [8.9,35.3]|0/32; 0.0% [0.0,10.7]|3|12/32; 37.5% [22.9,54.7]|0/0; undefined|
|clock_lag|plume-weather-0.5.0|6/32; 18.8% [8.9,35.3]|0/32; 0.0% [0.0,10.7]|0|14/32; 43.8% [28.2,60.7]|0/0; undefined|
|distant_station|baseline-0.4.0|0/0; undefined|0/0; undefined|0|0/0; undefined|0/0; undefined|
|distant_station|plume-weather-0.5.0|0/0; undefined|0/0; undefined|0|0/0; undefined|0/0; undefined|
|spatial_winds|baseline-0.4.0|2/32; 6.2% [1.7,20.1]|0/32; 0.0% [0.0,10.7]|14|16/32; 50.0% [33.6,66.4]|0/0; undefined|
|spatial_winds|plume-weather-0.5.0|1/32; 3.1% [0.6,15.7]|0/32; 0.0% [0.0,10.7]|5|16/32; 50.0% [33.6,66.4]|0/0; undefined|
|variable_weather|baseline-0.4.0|0/0; undefined|0/0; undefined|0|0/0; undefined|0/0; undefined|
|variable_weather|plume-weather-0.5.0|0/0; undefined|0/0; undefined|0|0/0; undefined|0/0; undefined|
|weak|baseline-0.4.0|0/32; 0.0% [0.0,10.7]|0/32; 0.0% [0.0,10.7]|7|32/32; 100.0% [89.3,100.0]|0/0; undefined|
|weak|plume-weather-0.5.0|0/32; 0.0% [0.0,10.7]|0/32; 0.0% [0.0,10.7]|5|32/32; 100.0% [89.3,100.0]|0/0; undefined|
|correlated|baseline-0.4.0|23/32; 71.9% [54.6,84.4]|0/32; 0.0% [0.0,10.7]|2|7/32; 21.9% [11.0,38.8]|0/0; undefined|
|correlated|plume-weather-0.5.0|18/32; 56.2% [39.3,71.8]|0/32; 0.0% [0.0,10.7]|3|3/32; 9.4% [3.2,24.2]|0/0; undefined|
|two_sources|baseline-0.4.0|2/32; 6.2% [1.7,20.1]|0/32; 0.0% [0.0,10.7]|6|5/32; 15.6% [6.9,31.8]|0/0; undefined|
|two_sources|plume-weather-0.5.0|1/32; 3.1% [0.6,15.7]|0/32; 0.0% [0.0,10.7]|5|5/32; 15.6% [6.9,31.8]|0/0; undefined|
|background|baseline-0.4.0|0/32; 0.0% [0.0,10.7]|0/32; 0.0% [0.0,10.7]|0|0/0; undefined|0/32; 0.0% [0.0,10.7]|
|background|plume-weather-0.5.0|0/32; 0.0% [0.0,10.7]|0/32; 0.0% [0.0,10.7]|0|0/0; undefined|0/32; 0.0% [0.0,10.7]|
|independent_transport|baseline-0.4.0|2/32; 6.2% [1.7,20.1]|0/32; 0.0% [0.0,10.7]|4|13/32; 40.6% [25.5,57.7]|0/0; undefined|
|independent_transport|plume-weather-0.5.0|2/32; 6.2% [1.7,20.1]|0/32; 0.0% [0.0,10.7]|3|13/32; 40.6% [25.5,57.7]|0/0; undefined|

## All, accepted and rejected distributions

Each error cell is p10 / median / p90 / maximum in metres. Area cells give mean and p10 / median / p90 / maximum as percentage of supported domain. Refusals have no fitted error/area and remain in generated rates above. Conditional-mean error and no-data centroid comparisons are retained in final-summary.json along with source Brier and runtime.

| Condition | Model | Group (n) | MAP error m | Conditional mean error m | Region area % |
|---|---|---|---|---|---|
|characterized_nominal|baseline-0.4.0|all (32)|12.4 / 37.2 / 196.6 / 415.1|14.4 / 99.4 / 183.4 / 275.4|mean 43.6; 3.3 / 54.7 / 69.3 / 77.6|
|characterized_nominal|baseline-0.4.0|accepted (11)|7.7 / 25.8 / 173.2 / 207.5|7.7 / 15.1 / 99.4 / 116.5|mean 11.8; 1.8 / 10.3 / 22.7 / 28.1|
|characterized_nominal|baseline-0.4.0|rejected (21)|19.0 / 74.7 / 199.2 / 415.1|73.5 / 108.5 / 224.8 / 275.4|mean 60.3; 50.6 / 60.4 / 70.3 / 77.6|
|characterized_nominal|plume-weather-0.5.0|all (32)|14.5 / 51.3 / 207.1 / 415.1|13.4 / 101.2 / 188.7 / 275.2|mean 45.1; 4.0 / 55.7 / 71.1 / 78.9|
|characterized_nominal|plume-weather-0.5.0|accepted (11)|7.7 / 30.9 / 154.7 / 207.5|8.4 / 23.0 / 96.9 / 118.3|mean 13.4; 1.8 / 12.4 / 24.7 / 31.6|
|characterized_nominal|plume-weather-0.5.0|rejected (21)|15.8 / 64.9 / 256.6 / 415.1|64.5 / 112.0 / 224.0 / 275.2|mean 61.7; 51.3 / 62.7 / 71.6 / 78.9|
|unknown_nominal|baseline-0.4.0|all (32)|12.4 / 37.2 / 196.6 / 415.1|14.4 / 99.4 / 183.4 / 275.4|mean 43.6; 3.3 / 54.7 / 69.3 / 77.6|
|unknown_nominal|baseline-0.4.0|accepted (11)|7.7 / 25.8 / 173.2 / 207.5|7.7 / 15.1 / 99.4 / 116.5|mean 11.8; 1.8 / 10.3 / 22.7 / 28.1|
|unknown_nominal|baseline-0.4.0|rejected (21)|19.0 / 74.7 / 199.2 / 415.1|73.5 / 108.5 / 224.8 / 275.4|mean 60.3; 50.6 / 60.4 / 70.3 / 77.6|
|unknown_nominal|plume-weather-0.5.0|all (32)|19.2 / 58.9 / 257.5 / 518.9|18.3 / 134.5 / 210.6 / 268.6|mean 64.0; 13.0 / 76.9 / 83.0 / 85.8|
|unknown_nominal|plume-weather-0.5.0|accepted (8)|18.9 / 31.0 / 105.1 / 191.8|7.8 / 34.6 / 102.2 / 135.4|mean 23.3; 1.9 / 22.2 / 46.0 / 49.7|
|unknown_nominal|plume-weather-0.5.0|rejected (24)|21.7 / 72.2 / 259.4 / 518.9|75.7 / 149.5 / 221.7 / 268.6|mean 77.6; 68.3 / 78.8 / 84.0 / 85.8|
|direction_unknown|baseline-0.4.0|all (32)|104.7 / 228.3 / 386.4 / 518.9|88.0 / 195.6 / 270.6 / 329.5|mean 47.4; 4.1 / 60.8 / 75.4 / 77.8|
|direction_unknown|baseline-0.4.0|accepted (7)|88.1 / 134.6 / 255.8 / 323.6|88.1 / 135.7 / 235.3 / 271.0|mean 8.9; 0.4 / 7.3 / 19.1 / 20.6|
|direction_unknown|baseline-0.4.0|rejected (25)|105.1 / 280.8 / 414.2 / 518.9|94.8 / 202.7 / 283.1 / 329.5|mean 58.2; 22.7 / 66.1 / 76.6 / 77.8|
|direction_unknown|plume-weather-0.5.0|all (32)|24.8 / 172.8 / 367.0 / 443.5|49.2 / 164.6 / 242.4 / 267.4|mean 63.3; 13.0 / 77.9 / 85.1 / 85.6|
|direction_unknown|plume-weather-0.5.0|accepted (9)|20.8 / 109.8 / 205.2 / 214.5|23.9 / 58.2 / 127.0 / 156.7|mean 28.2; 5.1 / 31.6 / 46.1 / 48.3|
|direction_unknown|plume-weather-0.5.0|rejected (23)|38.5 / 219.3 / 380.9 / 443.5|129.6 / 178.6 / 246.4 / 267.4|mean 77.1; 74.1 / 82.2 / 85.3 / 85.6|
|direction_characterized|baseline-0.4.0|all (32)|104.7 / 228.3 / 386.4 / 518.9|88.0 / 195.6 / 270.6 / 329.5|mean 47.4; 4.1 / 60.8 / 75.4 / 77.8|
|direction_characterized|baseline-0.4.0|accepted (7)|88.1 / 134.6 / 255.8 / 323.6|88.1 / 135.7 / 235.3 / 271.0|mean 8.9; 0.4 / 7.3 / 19.1 / 20.6|
|direction_characterized|baseline-0.4.0|rejected (25)|105.1 / 280.8 / 414.2 / 518.9|94.8 / 202.7 / 283.1 / 329.5|mean 58.2; 22.7 / 66.1 / 76.6 / 77.8|
|direction_characterized|plume-weather-0.5.0|all (32)|15.9 / 37.9 / 126.0 / 351.9|17.1 / 100.2 / 213.0 / 289.7|mean 43.6; 6.1 / 50.1 / 73.8 / 78.7|
|direction_characterized|plume-weather-0.5.0|accepted (10)|18.0 / 34.3 / 67.1 / 73.5|7.6 / 22.5 / 55.7 / 66.2|mean 15.2; 3.2 / 17.3 / 23.4 / 23.8|
|direction_characterized|plume-weather-0.5.0|rejected (22)|12.7 / 49.6 / 209.2 / 351.9|55.4 / 127.6 / 218.9 / 289.7|mean 56.6; 25.7 / 62.5 / 74.7 / 78.7|
|speed_bias|baseline-0.4.0|all (32)|8.1 / 43.2 / 126.0 / 371.0|14.7 / 106.3 / 212.6 / 287.8|mean 41.6; 3.9 / 50.6 / 72.4 / 78.7|
|speed_bias|baseline-0.4.0|accepted (10)|7.4 / 42.0 / 68.5 / 87.1|9.1 / 22.6 / 47.1 / 63.6|mean 12.9; 2.7 / 14.0 / 20.6 / 20.8|
|speed_bias|baseline-0.4.0|rejected (22)|11.2 / 43.5 / 192.1 / 371.0|58.5 / 127.4 / 218.9 / 287.8|mean 54.7; 25.4 / 59.4 / 73.0 / 78.7|
|speed_bias|plume-weather-0.5.0|all (32)|17.7 / 68.7 / 249.2 / 423.4|21.4 / 134.9 / 227.6 / 253.3|mean 63.1; 11.9 / 76.9 / 83.1 / 85.4|
|speed_bias|plume-weather-0.5.0|accepted (6)|19.6 / 39.2 / 69.7 / 74.4|5.6 / 25.0 / 63.0 / 69.0|mean 23.3; 3.5 / 22.8 / 43.5 / 48.5|
|speed_bias|plume-weather-0.5.0|rejected (26)|20.4 / 73.3 / 257.5 / 423.4|54.5 / 143.8 / 230.2 / 253.3|mean 72.3; 58.2 / 79.2 / 83.2 / 85.4|
|clock_lag|baseline-0.4.0|all (32)|41.8 / 102.8 / 220.1 / 245.9|57.7 / 89.8 / 204.1 / 254.4|mean 41.0; 5.5 / 44.5 / 71.1 / 74.6|
|clock_lag|baseline-0.4.0|accepted (4)|19.3 / 38.7 / 79.4 / 95.8|23.0 / 36.1 / 84.2 / 99.9|mean 10.6; 4.2 / 10.2 / 17.5 / 19.0|
|clock_lag|baseline-0.4.0|rejected (28)|47.5 / 115.5 / 223.1 / 245.9|64.2 / 92.0 / 212.9 / 254.4|mean 45.3; 5.8 / 58.2 / 71.3 / 74.6|
|clock_lag|plume-weather-0.5.0|all (32)|39.6 / 84.2 / 241.6 / 439.6|54.8 / 114.6 / 197.4 / 266.7|mean 60.1; 13.2 / 74.3 / 83.0 / 85.8|
|clock_lag|plume-weather-0.5.0|accepted (3)|42.2 / 55.4 / 66.3 / 69.1|31.6 / 43.8 / 67.2 / 73.0|mean 24.5; 10.8 / 14.4 / 42.2 / 49.2|
|clock_lag|plume-weather-0.5.0|rejected (29)|43.3 / 96.0 / 244.5 / 439.6|76.3 / 115.4 / 203.3 / 266.7|mean 63.8; 16.2 / 77.1 / 83.1 / 85.8|
|distant_station|baseline-0.4.0|all (0)|—|—|—|
|distant_station|baseline-0.4.0|accepted (0)|—|—|—|
|distant_station|baseline-0.4.0|rejected (0)|—|—|—|
|distant_station|plume-weather-0.5.0|all (0)|—|—|—|
|distant_station|plume-weather-0.5.0|accepted (0)|—|—|—|
|distant_station|plume-weather-0.5.0|rejected (0)|—|—|—|
|spatial_winds|baseline-0.4.0|all (32)|75.1 / 196.7 / 338.3 / 447.8|79.7 / 174.4 / 266.7 / 303.9|mean 41.1; 6.2 / 51.4 / 70.5 / 74.8|
|spatial_winds|baseline-0.4.0|accepted (11)|62.5 / 174.4 / 261.1 / 265.5|94.4 / 173.9 / 231.7 / 269.4|mean 11.9; 6.2 / 10.5 / 21.3 / 30.7|
|spatial_winds|baseline-0.4.0|rejected (21)|86.2 / 214.2 / 364.8 / 447.8|73.0 / 174.8 / 287.4 / 303.9|mean 56.3; 25.4 / 65.0 / 70.7 / 74.8|
|spatial_winds|plume-weather-0.5.0|all (32)|60.4 / 162.6 / 341.4 / 518.9|54.9 / 145.8 / 228.0 / 284.4|mean 60.9; 26.2 / 72.7 / 83.5 / 84.2|
|spatial_winds|plume-weather-0.5.0|accepted (10)|54.9 / 127.5 / 229.7 / 278.3|52.8 / 120.4 / 180.3 / 191.1|mean 31.9; 22.0 / 30.4 / 41.9 / 44.4|
|spatial_winds|plume-weather-0.5.0|rejected (22)|79.5 / 164.3 / 357.3 / 518.9|59.0 / 170.2 / 254.4 / 284.4|mean 74.1; 61.4 / 81.6 / 83.7 / 84.2|
|variable_weather|baseline-0.4.0|all (0)|—|—|—|
|variable_weather|baseline-0.4.0|accepted (0)|—|—|—|
|variable_weather|baseline-0.4.0|rejected (0)|—|—|—|
|variable_weather|plume-weather-0.5.0|all (0)|—|—|—|
|variable_weather|plume-weather-0.5.0|accepted (0)|—|—|—|
|variable_weather|plume-weather-0.5.0|rejected (0)|—|—|—|
|weak|baseline-0.4.0|all (32)|77.4 / 213.1 / 384.3 / 488.1|77.5 / 194.2 / 284.2 / 315.2|mean 71.1; 66.4 / 72.1 / 75.5 / 78.5|
|weak|baseline-0.4.0|accepted (0)|—|—|—|
|weak|baseline-0.4.0|rejected (32)|77.4 / 213.1 / 384.3 / 488.1|77.5 / 194.2 / 284.2 / 315.2|mean 71.1; 66.4 / 72.1 / 75.5 / 78.5|
|weak|plume-weather-0.5.0|all (32)|117.4 / 324.7 / 438.4 / 518.9|91.8 / 184.2 / 250.2 / 284.0|mean 83.0; 80.2 / 83.6 / 84.6 / 85.8|
|weak|plume-weather-0.5.0|accepted (0)|—|—|—|
|weak|plume-weather-0.5.0|rejected (32)|117.4 / 324.7 / 438.4 / 518.9|91.8 / 184.2 / 250.2 / 284.0|mean 83.0; 80.2 / 83.6 / 84.6 / 85.8|
|correlated|baseline-0.4.0|all (32)|14.6 / 118.1 / 317.6 / 457.2|12.0 / 130.9 / 247.1 / 460.2|mean 27.2; 3.9 / 20.8 / 63.2 / 76.2|
|correlated|baseline-0.4.0|accepted (5)|21.2 / 45.8 / 229.1 / 234.6|9.7 / 73.5 / 267.5 / 302.0|mean 13.1; 3.2 / 10.5 / 24.3 / 24.7|
|correlated|baseline-0.4.0|rejected (27)|13.0 / 119.0 / 351.8 / 457.2|16.6 / 131.8 / 240.9 / 460.2|mean 29.8; 4.2 / 21.3 / 65.4 / 76.2|
|correlated|plume-weather-0.5.0|all (32)|45.3 / 193.7 / 343.2 / 480.9|26.7 / 145.3 / 228.4 / 477.8|mean 45.2; 8.3 / 48.4 / 75.6 / 82.8|
|correlated|plume-weather-0.5.0|accepted (5)|41.6 / 99.3 / 253.5 / 328.1|39.5 / 175.7 / 214.5 / 228.5|mean 30.4; 16.5 / 31.6 / 41.6 / 42.1|
|correlated|plume-weather-0.5.0|rejected (27)|55.1 / 196.8 / 360.6 / 480.9|40.8 / 140.2 / 231.0 / 477.8|mean 47.9; 7.4 / 52.6 / 75.8 / 82.8|
|two_sources|baseline-0.4.0|all (32)|24.0 / 95.0 / 250.2 / 383.0|13.8 / 101.2 / 249.5 / 330.6|mean 28.1; 3.0 / 18.2 / 66.3 / 68.0|
|two_sources|baseline-0.4.0|accepted (16)|20.7 / 82.1 / 315.6 / 383.0|9.5 / 80.6 / 302.1 / 330.6|mean 11.6; 2.7 / 10.8 / 19.0 / 29.5|
|two_sources|baseline-0.4.0|rejected (16)|37.2 / 118.1 / 187.4 / 301.6|22.0 / 124.7 / 173.1 / 251.2|mean 44.7; 15.0 / 46.0 / 67.4 / 68.0|
|two_sources|plume-weather-0.5.0|all (32)|25.0 / 100.3 / 240.9 / 365.4|43.1 / 137.5 / 229.8 / 273.1|mean 51.2; 12.6 / 49.4 / 81.1 / 83.3|
|two_sources|plume-weather-0.5.0|accepted (13)|21.9 / 56.7 / 305.0 / 365.4|29.3 / 87.3 / 267.5 / 273.1|mean 31.1; 7.6 / 34.1 / 47.5 / 48.5|
|two_sources|plume-weather-0.5.0|rejected (19)|42.8 / 100.4 / 228.1 / 328.4|52.8 / 152.4 / 199.8 / 232.8|mean 65.0; 46.4 / 73.0 / 81.6 / 83.3|
|background|baseline-0.4.0|all (32)|—|—|mean 69.9; 65.5 / 70.4 / 74.1 / 74.6|
|background|baseline-0.4.0|accepted (0)|—|—|—|
|background|baseline-0.4.0|rejected (32)|—|—|mean 69.9; 65.5 / 70.4 / 74.1 / 74.6|
|background|plume-weather-0.5.0|all (32)|—|—|mean 82.9; 80.4 / 83.2 / 84.4 / 85.8|
|background|plume-weather-0.5.0|accepted (0)|—|—|—|
|background|plume-weather-0.5.0|rejected (32)|—|—|mean 82.9; 80.4 / 83.2 / 84.4 / 85.8|
|independent_transport|baseline-0.4.0|all (32)|14.9 / 57.6 / 259.1 / 357.1|25.4 / 87.5 / 217.5 / 278.4|mean 35.3; 2.4 / 25.7 / 68.8 / 72.8|
|independent_transport|baseline-0.4.0|accepted (13)|10.5 / 48.0 / 191.7 / 313.6|13.8 / 39.0 / 132.9 / 249.9|mean 6.2; 1.8 / 6.9 / 11.4 / 11.9|
|independent_transport|baseline-0.4.0|rejected (19)|42.5 / 83.5 / 281.5 / 357.1|58.6 / 135.0 / 221.7 / 278.4|mean 55.2; 18.3 / 64.1 / 69.6 / 72.8|
|independent_transport|plume-weather-0.5.0|all (32)|14.6 / 80.0 / 311.7 / 473.2|18.9 / 93.1 / 219.0 / 283.2|mean 36.8; 2.6 / 28.0 / 69.7 / 74.6|
|independent_transport|plume-weather-0.5.0|accepted (13)|12.2 / 30.2 / 191.7 / 313.6|12.4 / 40.5 / 132.2 / 249.3|mean 7.3; 1.7 / 8.2 / 13.0 / 16.0|
|independent_transport|plume-weather-0.5.0|rejected (19)|29.5 / 160.0 / 330.1 / 473.2|59.1 / 140.8 / 222.6 / 283.2|mean 56.9; 20.4 / 65.0 / 71.9 / 74.6|
