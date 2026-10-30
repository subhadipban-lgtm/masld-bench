# MB-89xx classical gates (2026-10-29, frozen §9)

logreg + HGB, stratified 5-fold OOF (seed 20260929), 2000 bootstraps. Features = the prompt panel (top-200 MAD, CPM->log1p->z).

## 8901_anchor_binary
```json
{
 "logreg": {
  "acc": 0.7232,
  "ci": [
   0.6429,
   0.8036
  ],
  "chance": 0.5,
  "majority": 0.3036,
  "beats_chance": true,
  "beats_majority": true
 },
 "hgb": {
  "acc": 0.6875,
  "ci": [
   0.5982,
   0.7768
  ],
  "chance": 0.5,
  "majority": 0.3036,
  "beats_chance": true,
  "beats_majority": true
 }
}
```
## 8902_anchor_5class
```json
{
 "logreg": {
  "acc": 0.3393,
  "ci": [
   0.25,
   0.4286
  ],
  "chance": 0.2,
  "majority": 0.3036,
  "beats_chance": true,
  "beats_majority": false
 },
 "hgb": {
  "acc": 0.2857,
  "ci": [
   0.2054,
   0.375
  ],
  "chance": 0.2,
  "majority": 0.3036,
  "beats_chance": true,
  "beats_majority": false
 }
}
```
## 8905_anchor_ordinal
```json
{
 "logreg": {
  "mae": 1.1339,
  "ci": [
   0.9554,
   1.3214
  ],
  "median_mae": 1.5,
  "beats_median": true,
  "rho": 0.3272
 },
 "hgb": {
  "mae": 1.1518,
  "ci": [
   1.0,
   1.3214
  ],
  "median_mae": 1.5,
  "beats_median": true,
  "rho": 0.2553
 }
}
```
## 8921_amc_binary
```json
{
 "logreg": {
  "acc": 0.6296,
  "ci": [
   0.537,
   0.7222
  ],
  "chance": 0.5,
  "majority": 0.3056,
  "beats_chance": true,
  "beats_majority": true
 },
 "hgb": {
  "acc": 0.6204,
  "ci": [
   0.5278,
   0.713
  ],
  "chance": 0.5,
  "majority": 0.3056,
  "beats_chance": true,
  "beats_majority": true
 }
}
```
## 8922_amc_5class
```json
{
 "logreg": {
  "acc": 0.2685,
  "ci": [
   0.1852,
   0.3519
  ],
  "chance": 0.2,
  "majority": 0.3056,
  "beats_chance": false,
  "beats_majority": false
 },
 "hgb": {
  "acc": 0.2315,
  "ci": [
   0.1574,
   0.3148
  ],
  "chance": 0.2,
  "majority": 0.3056,
  "beats_chance": false,
  "beats_majority": false
 }
}
```
## 8925_amc_ordinal
```json
{
 "logreg": {
  "mae": 1.1481,
  "ci": [
   0.9815,
   1.3241
  ],
  "median_mae": 2.0,
  "beats_median": true,
  "rho": 0.1978
 },
 "hgb": {
  "mae": 0.963,
  "ci": [
   0.8241,
   1.1019
  ],
  "median_mae": 2.0,
  "beats_median": true,
  "rho": 0.305
 }
}
```
## label_noise_logreg
```json
{
 "acc_vs_uza": 0.3889,
 "acc_vs_amc": 0.2593,
 "gap": 0.1296
}
```
## 8911_ext_binary
```json
{
 "logreg": {
  "acc": 0.6201,
  "ci": [
   0.5529,
   0.6872
  ],
  "chance": 0.5,
  "majority": 0.3352,
  "beats_chance": true,
  "beats_majority": true
 },
 "hgb": {
  "acc": 0.5754,
  "ci": [
   0.5028,
   0.648
  ],
  "chance": 0.5,
  "majority": 0.3352,
  "beats_chance": true,
  "beats_majority": true
 }
}
```
## 8912_ext_5class
```json
{
 "logreg": {
  "acc": 0.2905,
  "ci": [
   0.2235,
   0.3521
  ],
  "chance": 0.2,
  "majority": 0.3352,
  "beats_chance": true,
  "beats_majority": false
 },
 "hgb": {
  "acc": 0.3073,
  "ci": [
   0.2402,
   0.3743
  ],
  "chance": 0.2,
  "majority": 0.3352,
  "beats_chance": true,
  "beats_majority": false
 }
}
```
## 8915_ext_ordinal
```json
{
 "logreg": {
  "mae": 1.6257,
  "ci": [
   1.4302,
   1.8158
  ],
  "median_mae": 2.0,
  "beats_median": true,
  "rho": 0.1255
 },
 "hgb": {
  "mae": 1.2402,
  "ci": [
   1.1173,
   1.3687
  ],
  "median_mae": 2.0,
  "beats_median": true,
  "rho": 0.2822
 }
}
```
