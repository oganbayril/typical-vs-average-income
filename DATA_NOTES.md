# Data notes

Source checks for the candidate measures. Verified 2026-10-16 by downloading
each dataset (Eurostat, OECD) or reading only the needed files out of the WID
bulk zip. Scope = same country list as food-housing-spending-share: EU27, EFTA,
UK, candidates (incl. Kosovo, Bosnia) and all 38 OECD members.

Year conventions used below:
- **Eurostat** years are **survey years**. The income behind them is from the
  year before (except Ireland and the UK, which use a rolling 12 months).
- **OECD IDD** years are **income years**.
- **WID** years are income years.

## 1. Datasets

| Measure | Source | Code | Filter used | Unit | Latest |
|---|---|---|---|---|---|
| Median income | Eurostat | `ilc_di03` | `statinfo=MED_EI, age=TOTAL, sex=T` | EUR, NAC, **PPS** | 2025 |
| Mean income | Eurostat | `ilc_di03` | `statinfo=MEAN_EI`, same | EUR, NAC, PPS | 2025 |
| Median and mean income | OECD | `OECD.WISE.INE,DSD_WISE_IDD@DF_IDD` | `MEASURE=INC_DISP, STATISTICAL_OPERATION=MEDIAN/MEAN, AGE=_T, METHODOLOGY=METH2012, DEFINITION=D_CUR` | `XDC_HH_EQ` (national currency per equivalised household), current prices | 2023 (FIN, SWE, NLD 2024; CRI 2025) |
| Severe material and social deprivation rate | Eurostat | `ilc_mdsd11` | `age=TOTAL, sex=T, unit=PC` | % of population | 2025 |
| At-risk-of-poverty rate (60% of median) | Eurostat | `ilc_li02` | `statinfo=MED_EI, rskpovth=B_60, age=TOTAL, sex=T, unit=PC` | % | 2025 |
| Can't face unexpected expenses | Eurostat | `ilc_mdes04` | `hhcomp=TOTAL, rskpovth=TOTAL, unit=PC` | % | 2025 |
| Making ends meet with (great) difficulty | Eurostat | `ilc_mdes09` | `lev_diff=GRT` (+ `DIF`), `hhcomp=TOTAL, rskpovth=TOTAL` | % | 2025 |
| At risk of poverty or social exclusion (AROPE, 2021 definition) | Eurostat | `ilc_peps01n` | `age=TOTAL, sex=T, unit=PC` | % | 2025 |
| Difficulty making ends meet | OECD How's Life | `OECD.WISE.WDP,DSD_HSL@DF_HSL_CWB`, `MEASURE=1_5` | `AGE=_T, SEX=_T` | % of population aged 16+ | 2025 |
| Top 10% income share | WID | `sptincj992`, percentile `p90p100` | from `WID_data_<CC>.csv` | share (0-1) of pretax national income, adults 20+, equal-split | 2024 |
| Top 10% share, post-tax disposable | WID | `sdiincj992`, `p90p100` | same | share (0-1) | 2024 |

Other things checked along the way:
- `ilc_di12` (Gini) is available, 2014-2025.
- Eurostat flags seen: `b` = break in series, `p` = provisional (LT 2024-25),
  `u` = low reliability (in `mdes04`/`mdes09` sub-cells).
- OECD IDD flags: `OBS_STATUS=P` (provisional), only NLD 2024 in the series used.
- WID has its own data-quality grade per observation (0-5, last column
  `data_quality`) and an average per series in the metadata (`avg_quality`).

## 2. Coverage matrix

Ranges are first-last year with data. "—" = no data. Gaps inside a range are
listed. "SILC set" = `ilc_li02`, `ilc_mdes04`, `ilc_mdes09`, which follow the
same years as `ilc_di03` unless noted. Eurostat years before 2003-2005 come
from an older survey (ECHP) and are left out here (see issue E1).

| Country | Eurostat income `ilc_di03` (survey yr) | MSD `ilc_mdsd11` | SILC set | OECD IDD (income yr) | WID top 10% (avg quality) |
|---|---|---|---|---|---|
| Austria | 2003-2025 | 2015-2025 | same | 2007-2023 | 1980-2024 (4.2) |
| Belgium | 2003-2025 | 2015-2025 | same | 2018-2023 (2003-17 old definition) | (3.5) |
| Bulgaria | 2006-2025 | 2015-2025 | same | 2006-2023 | (2.8) |
| Croatia | 2010-2025 | 2015-2025 | same | 2009-2023 | (3.5) |
| Cyprus | 2005-2025 | 2015-2025 | same | — | (3.0) |
| Czechia | 2005-2025 | 2015-2025 | same | 2004-2023 | (3.6) |
| Denmark | 2003-2025 | 2015-2025 | same | 2011-2022 | (3.3) |
| Estonia | 2004-2025 | 2015-2025 | same | 2013-2023 (2003-12 old) | (3.7) |
| Finland | 2004-2025 | 2015-2025 | same | 1987-2024 | (3.4) |
| France | 2004-2025 | 2015-2025 | same | 2020-2023 (2011-20 old) | (4.8) |
| Germany | 2005-2025 | 2015-2025 | same | 2008, 2011-2023 | (3.5) |
| Greece | 2003-2025 | 2015-2025 | same | 2003-2023 | (3.7) |
| Hungary | 2005-2025 | 2015-2025 | same | 2004-2017, 2023 | (2.8) |
| Ireland | 2003-2025 | 2015-2025 | same | 2003-2023 | (3.6) |
| Italy | 2004-2025 | 2015-2025 | same | 2003-2023 | (3.8) |
| Latvia | 2005-2025 | 2015-2025 | same | 2004-2023 | (3.0) |
| Lithuania | 2005-2025 | 2015-2025 | same | 2004-2023 | (3.0) |
| Luxembourg | 2003-2025 | 2015-2025 | same | 2015-2023 (2003-14 old) | (3.4) |
| Malta | 2005-2025 | 2015-2025 | same | — | (2.5) |
| Netherlands | 2005-2025 | 2015-2025 | same | 2011-2024 (2024 provisional) | (3.6) |
| Poland | 2005-2025 | 2015-2025 | same | 2005-2023 | (3.6) |
| Portugal | 2004-2025 | 2015-2025 | same | 2003-2023 | (3.6) |
| Romania | 2007-2025 | 2015-2025 | same | 2006-2023 | (3.0) |
| Slovakia | 2005-2025 | 2015-2025 | same | 2004-2023 | (3.0) |
| Slovenia | 2005-2025 | 2015-2025 | same | 2004-2023 | (3.4) |
| Spain | 2004-2025 | 2015-2025 | same | 2007-2023 (2003-06 old) | (3.5) |
| Sweden | 2004-2025 | 2015-2025 | same | 2013-2024 | (3.5) |
| Iceland | 2004-2020 | 2015-2020 | same | 2003-2019 | (3.3) |
| Liechtenstein | — | — | — | — | (0.0, no own data) |
| Norway | 2003-2025 | 2015-2025, no 2016 | same | 2004, 2008-2023 | (3.4) |
| Switzerland | 2007-2024 | 2015-2024 | same | 2006-2023 | (3.5) |
| United Kingdom | 2005-2018 | 2015-2018 | same | 2002-2023 | (3.4) |
| Albania | 2017-2023 | 2017-2023 | same (`li02` to 2024) | — | (2.3) |
| Bosnia and Herzegovina | — | — | — | — | (2.2) |
| Kosovo | 2018 only | — | 2018 (`li02` 2018-19) | — | (2.1, WID code `KS`) |
| Montenegro | 2013-2024 | 2015-2024 | same | — | (1.0) |
| North Macedonia | 2012-2024 | 2015-2024 | 2010-2024 | — | (1.0) |
| Serbia | 2013-2025 | 2015-2025, no 2016 | same | — | (3.0) |
| Türkiye | 2006-2025 | 2017-2025 | same; `mdes04` no 2010, `mdes09` no 2010, 2019 | 2011-2015, 2017-2022 | (2.8) |
| Australia | — | — | — | 2012-2020, every 2 yrs | (5.0) |
| Canada | — | — | (How's Life: 2018, 2021) | 1976-2023 | (5.0) |
| Chile | — | — | — | 2009-2022, 7 yrs | (2.6) |
| Colombia | — | — | — | **— (not in IDD)** | (3.1) |
| Costa Rica | — | — | — | 2010-2025 | (3.9) |
| Israel | — | — | — | 2023 only (2011-22 old) | (1.9) |
| Japan | — | — | — | 2018, 2021 | (1.4) |
| Mexico | — | — | (How's Life: 2021) | 2012-2022, every 2 yrs | (2.5) |
| New Zealand | — | — | (How's Life: 2008-21, 7 yrs) | 2006-2022 | (4.9) |
| South Korea | — | — | — | 2011-2023 | (3.4) |
| United States | — | — | — | 2013-2023 | (5.0) |

WID covers every country listed for 1980-2024 (it imputes where it lacks
data, which is why the quality grade matters). The latest year (2024) is
graded 1 (projection) for DE, MT, KS and CO, but not for TR (3) or US (5).

Break flags (`b`) in `ilc_di03` since 2005: AT 2008, BE 2019, BG 2016,
CY 2008, DE 2020, DK 2011/2020, EE 2014, FR 2008/2020/2022, HR 2023/2024,
HU 2019, IE 2019/2020, LU 2016/2020/2021/2022/2025, NL 2016, SE 2008, SK 2025,
CH 2014, NO 2021/2023, UK 2012/2017, MK 2021. Most also show up in the other
SILC datasets. `ilc_mdsd11` has fewer: DE 2020, FR 2020/2022, HU 2019,
IE 2019/2020, LU 2020-22/2025, NO 2021, MK 2021. No break flags for Türkiye in
any dataset checked.

## 3. Issues

**E1. Don't splice ECHP and EU-SILC.** `ilc_di03` and `ilc_li02` go back to
1995 for old member states, but up to about 2001 the figures come from the
older survey (ECHP). They carry a `b` flag at 2003-2005 and the series have
gaps in between. Start Eurostat series at the first EU-SILC year.

**E2. Never mix Eurostat and OECD income levels.** The OECD median is 5-35%
higher than Eurostat's for the same country and year. Example for 2021 income,
national currency: Germany 24,925 vs 28,160; Türkiye 29,477 vs 35,830. The
likely cause is that OECD divides by the square root of household size, while
Eurostat uses the "modified OECD" scale. The PPS unit also exists only in
Eurostat.

**E3. Year labels differ by one.** Eurostat survey year N ≈ OECD year N-1.
After that shift, median/mean ratios agree to within 0.01 for EL, ES, IT, CH,
BG, FR and DE (2021), but differ by 0.02-0.03 for SE, TR and PL.

**E4. Median/mean ratio has no unit.** Currency and PPS cancel out. But the
equivalence scale (E2) still affects it slightly, so even the ratio should
come from one source per map. If OECD is used for non-European members, it is
a different source and needs a visible note.

**E5. Deprivation measures are effectively Europe-only.** OECD How's Life
"difficulty making ends meet" is the Eurostat figure republished (`GRT` + `DIF`
match exactly for DE, FR and TR). Outside Europe it only has Canada (2
years), Mexico (1) and New Zealand (7). With a deprivation measure, about 11
OECD members would be grey on the map.

**E6. MSD starts in 2015.** `ilc_mdsd11` uses the EU 2030 definition with 13
items, so there is no longer series. For Türkiye it starts in 2017. The older
"material deprivation" series is a different indicator.

**E7. WID measures a different thing from the surveys.** It uses pretax
national income, adults 20+, income split equally within couples, and
combines surveys, tax data and national accounts. Top-10% shares are much
higher than survey-based figures (2024: Türkiye 0.544, Germany 0.377,
US 0.468, Colombia 0.599). Never compare them with an S80/S20 or a survey
share. Other caveats:
- Liechtenstein is graded 0 throughout (imputed from the region).
- ME and MK average grade 1.0; JP 1.4; IL 1.9.
- Post-tax `sdiincj992` for 2019-2022 is extrapolated from the 2019 ratio
  (per WID metadata), so it's not usable for recent years.

**E8. Gaps in the country list.**
- Bosnia and Herzegovina and Liechtenstein: no Eurostat or OECD data.
- Kosovo: Eurostat 2018 only.
- UK: Eurostat stops in 2018; OECD runs to 2023.
- Iceland: Eurostat stops in 2020.
- Colombia: not in OECD IDD.
- Japan: 2 IDD years; Israel: 1 IDD year on the current definition.

**E9. Currency switch.** OECD reports Bulgaria in EUR (Eurostat NAC 9,020 vs
OECD 5,234 for the same year). This is fine for ratios, but watch for it if
national currency levels are ever used.

**E10. Odd series to check before use. Not fixed.**
- Türkiye "great difficulty or difficulty making ends meet" goes from 56.5%
  (2013) to 16.2% (2017), then back to 34.0% (2022), with no break flag.
- North Macedonia's median/mean ratio rises from 0.87 (2015) to 0.95 (2024);
  there is a break flag in 2021.
- Slovakia's ratio is 0.94-0.99 for 2015-2024, peaking at 0.990 in 2023, and
  has a break in 2025. It is consistently very compressed, so this is
  probably real, but it is the extreme of the range.

## 4. First look at the numbers (Eurostat, survey year 2024, 33-34 countries)

| Measure | Min | Median | Max | Lowest | Highest |
|---|---|---|---|---|---|
| Median/mean ratio | 0.677 | 0.886 | 0.978 | TR, BG, LT | NO, MK, SK |
| Median income, PPS | 8,971 | 20,800 | 37,781 | RS, MK, TR | CH, NO, LU |
| Severe material and social deprivation, % | 1.8 | 4.5 | 17.2 | SI, HR, LU | EL, BG, RO |
| At risk of poverty, % | 9.5 | 16.4 | 22.2 | CZ, BE, DK | BG, MK, TR |
| Can't face unexpected expenses, % | 16.9 | 28.7 | 48.0 | NL, MT, CZ | BG, MK, ME |
| Ends meet with (great) difficulty, % | 7.3 | 17.3 | 66.7 | NL, DE, LU | BG, MK, EL |

Spearman rank correlation across countries: the median/mean ratio is close to
0 with every other measure (-0.40 with poverty rate, about -0.1 to 0 with the
rest). The deprivation measures move together (0.47-0.71) and against median
PPS income (-0.61 to -0.79).

## 5. Checks after building the pipeline (2026-10-19)

Scripts: `src/check_robustness.py`, `src/probes/probe_suspicious.py`.

**R1. The year shift is right.** OECD income year N paired with Eurostat
survey year N+1: mean absolute difference 0.0091 (433 pairs). Unshifted:
0.0134 (422 pairs).

**R2. Eurostat vs OECD ratio, same country and year** (27 countries):
- 71% of pairs within 0.01, 95% within 0.03; median 0.0057, 90th
  percentile 0.0206, max 0.0622. Mean signed difference -0.001 (no overall
  bias).
- Per country (mean absolute difference): within 0.01 for 20 countries;
  0.01-0.03 for LUX, POL, DEU, SWE, TUR, NLD; over 0.03 for GBR (0.040, OECD
  always lower).
- Systematic: NLD (OECD -0.03 on average, -0.06 in 2024), SWE (-0.023),
  GBR (-0.040), TUR (+0.024). Germany is close on average, but 2024 differs
  by +0.032.
- Ranks (years with 10+ countries in both): a country moves 1 place at the
  median, 4 at the 90th percentile, 14 at most (NLD 2024: 9th in Eurostat,
  23rd in OECD).

**R3. Suspicious series** (data not altered):
- **Türkiye, making ends meet.** All six answers move together: "fairly
  easily" goes from 20% (2016) to 42% (2017) and back to 20% (2022), so the
  whole distribution shifts, not just neighbouring answers. Eurostat flags
  no break. TurkStat's SILC quality report (Eurostat metadata
  `ilc_simsilc_tr`) gives "Length of comparable time series = 2024 - 2014 +
  1", i.e. a break in 2014 that the database does not flag. That matches the
  2013-2014 step (also in `ilc_mdes04`: 49.0% to 29.0%). Nothing found
  explains 2017-2018. The poverty rate stays at 22-23% throughout.
  **Verdict:** 2014 step explained by an undocumented-in-database break;
  2017-2018 unexplained.
  - Consequence for the headline: Türkiye's median/mean ratio before 2014
    sits before that same break, without a flag in the data.
- **Slovakia, ratio 0.94-0.99.** Gini 20.9-24.3 (2014-2024), the lowest in
  the EU. OECD IDD gives 0.947-0.969 for the same years. Low inequality is
  real and confirmed by a second source. 2023 = 0.990: in Eurostat only
  (OECD 0.957). The median rose 4.5% while the mean rose 2.1%. The SK
  quality report lists no break up to 2024. 2025 has a `b` flag (ratio
  0.937, Gini 23.0). **Verdict:** level explained, 2023 spike unexplained.
- **North Macedonia, ratio 0.845 (2014) to 0.950 (2024).** Gini falls
  steadily from 35.2 to 29.2 over the same years. Mean and median both grow
  every year; the ratio rises because the median grows faster. Break flag in
  2021 (Gini 31.4 to 30.3, a small step). No OECD or other independent
  series to compare with; Eurostat's metadata page for MK was not found.
  **Verdict:** internally consistent trend; cause not verified; 2021 break
  unexplained.

**R4. Year labels after the shift.** Costa Rica's latest OECD income year
(2025) becomes survey year 2026, one year past the latest Eurostat year.
Canada's OECD series starts in 1977, long before any Eurostat data.

## 6. Decisions and checks (2026-10-21)

**D1. Latest-year snapshot for ended Eurostat series** (`build_snapshot.py`,
`decisions.EUROSTAT_DISCONTINUED`). UK, Iceland and Kosovo keep their
Eurostat history unchanged. Only in the snapshot, the OECD value is used,
marked `source = OECD`, if it is newer than Eurostat's last year.
- UK: Eurostat ends with survey year 2018. The snapshot shows OECD survey
  year 2024 (income 2023): 0.804. Measured offset where both exist (survey
  years 2005-2018): OECD minus Eurostat = -0.039 on average, -0.061 to
  -0.011. On Eurostat's method the UK would probably be about 0.84.
- Iceland: Eurostat ends 2020; OECD's latest is also 2020 (income 2019).
  Not newer, so it is grey.
- Kosovo: not an OECD member, so it is grey. (Kosovo was added to the rule
  by analogy; the decision named only the UK and Iceland.)

**D2. Project flags** (`decisions.PROJECT_FLAGS`, appended to the flag
column; values and source flags unchanged):
- `break_nso`: Türkiye 2014, making-ends-meet layer. Source: TurkStat SILC
  quality report on Eurostat's metadata page `ilc_simsilc_tr`, 15.2.1
  "Length of comparable time series = 2024 - 2014 + 1 = 11 years".
- `unexplained_outlier`: Slovakia 2023, headline ratio (0.990; OECD 0.957).

**D3. income_year column** in every layer (Eurostat survey year - 1, OECD as
published), used for display. Layer files keep income years 2002 onward
only. This drops 26 early Canada values (1976-2001), which stay in
`oecd_ratio.csv`. Costa Rica's latest value now displays as income year
2025.

**T1. Tier boundaries vs the ±0.03 source uncertainty**
(`src/probes/probe_tiers.py`, snapshot of 45 countries, income years
2020-2025, 41 of them 2023-2024).
- No boundary can be fully robust. The widest gap between neighbouring
  countries is 0.0575 (TUR 0.700 to MEX 0.758). Even at its midpoint, Mexico
  is 0.0275 away. A boundary with nobody within 0.03 would need a gap of at
  least 0.06.
- Gaps of 0.03 or more exist only below 0.84: 0.729, 0.775, 0.820
  (midpoints). Above that there is one gap of 0.018 (FIN 0.890 to NLD
  0.907, midpoint 0.8985). Between 0.836 and 0.890 sit 25 countries, with no
  gap over 0.008.
- Countries within ±0.03 of a boundary: 0.73 → 1 (MEX, OECD); 0.82 → 8 (2
  OECD: USA, GBR); 0.90 → 21 (3 OECD: ISR, KOR, CAN); 0.85 → 18 (5 OECD);
  0.80 → 3 (2 OECD).
- The UK's offset (-0.039) is larger than its distance to 0.82 (0.016), so
  its tier at that boundary depends on the source.

**D4. Tiers chosen (2026-10-21): scheme B**, boundaries 0.73 / 0.82 / 0.90
(`decisions.TIER_BOUNDARIES`). The snapshot gets `tier_uncertain = True` for
OECD-sourced countries within 0.03 (`decisions.SOURCE_UNCERTAINTY`) of a
boundary, with the note "Tier may differ under Eurostat's method": MEX,
USA, GBR, ISR, KOR, CAN. Eurostat countries are not marked, since the
±0.03 measures the difference between sources, not sampling error. Values
are unchanged. Kosovo stays grey (confirmed).
