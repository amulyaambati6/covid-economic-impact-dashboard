# Findings summary: COVID-19 and the economy

**Status:** authoritative findings document for the dashboard and presentation. It merges the two earlier versions (`findings_summary.md` and `findings_summaryy.md`, both generated from `notebooks/COVID_economy_EDA.ipynb`). Every figure below was recomputed from `data/processed/` on 2026-10-20, and the key figures are checked automatically by `tests/test_findings.py`.

**Countries studied (7):** Brazil, China, France, Germany, India, Rwanda, United States.
**Period:** economy 2018-2024; health and policy 2020-2022.
**Scope:** the dashboard question concerns the global economy, but these findings describe the seven countries above only.
**Method:** "own normal" means the country's average for 2018-2019 (two years only). Differences from it are in percentage points (pts).

## Headline findings by theme

| Theme | Main finding | Key figures | Countries |
|---|---|---|---|
| 1. Economic growth | Median GDP growth fell from 2.6% (2019) to -3.3% (2020), then rebounded to 6.9% (2021); 6 of 7 economies contracted in 2020. | Largest shortfalls vs own normal: Rwanda, India and France (-11.5, -10.9, -9.3 pts) | All 7; still growing in 2020: China |
| 2. Employment | Unemployment rose most in the United States (+4.4 pts) and fell in France; the median went 6.5% to 8.0% to 6.4%. | Later peaks: Rwanda (15.8% in 2021) | All 7 |
| 3. Prices and inflation | Inflation was low in 2020 (2.4% median) and peaked in 2022 (6.9% median). | Highest: 19.8% (Rwanda, 2023); largest 2022 rises: Rwanda, the United States and Brazil | All 7; below 3% throughout: China |
| 4. Global differences | Impact differed widely: Rwanda is most affected on average and China least; the economic loss did not follow reported deaths or restriction strictness. | Deaths vs GDP loss in 2020: rho +0.07 (n = 7); Rwanda most affected on 3 of 4 measures | All 7; highest reported deaths: Brazil and the United States; restrictions rose only in China |
| 5. Economic recovery | All 7 economies were above their 2019 size by 2022, but 6 of 7 remained below their pre-COVID growth trend in 2024. | Largest shortfall: Rwanda (-11%); above trend: Brazil (+3%) | All 7 |

## Theme 1. Economic growth
- Median GDP growth across the seven countries fell from 2.6% in 2019 to -3.3% in 2020 and rebounded to 6.9% in 2021.
- 6 of 7 economies contracted in 2020 (Brazil, France, Germany, India, Rwanda and the United States); China stayed positive (+2.3%) but far below its 2019 rate (6.1%).
- Against their own 2018-2019 average, the largest shortfalls in 2020 were in Rwanda, India and France (-11.5, -10.9, -9.3 points); all 7 countries grew less than their own normal.
- Caveat: Rwanda's large shortfall partly reflects its very fast 2018-2019 growth (8.7% a year). In raw growth, France (-7.4%) contracted more than Rwanda (-2.8%).

## Theme 2. Employment
- Unemployment rose most between 2019 and 2020 in the United States (+4.4 points, from 3.7% to 8.1%), followed by Brazil (+1.8) and India (+1.3); it fell in France.
- Measured against its 2018-2019 average instead of 2019 alone, the United States rise is +4.3 points (the dashboard shows both).
- Median unemployment across the seven countries went from 6.5% in 2019 to 8.0% in 2020 and 6.4% in 2021.
- In Rwanda the peak came later, in 2021 (15.8%).

## Theme 3. Prices and inflation
- Median inflation across the seven countries was 2.4% in 2020 and 6.9% in 2022: prices rose after the output and jobs shock, not during it.
- The largest rises in 2022 against each country's own 2018-2019 average were in Rwanda, the United States and Brazil (+16.2, +5.9, +5.6 points); the highest inflation recorded was 19.8% (Rwanda, 2023).
- Caveat: Rwanda's 2018 inflation was -0.3%, so its 2018-2019 baseline (1.5%) is unusually low, which enlarges its 2022 difference.
- China stayed below 3% throughout 2018-2024.

## Theme 4. Global differences
- Rwanda is the most affected country on 3 of the 4 economic measures (GDP loss (2020), Inflation rise (2022), Shortfall vs trend (2024)); on average across the four, Rwanda ranks as most affected and China as least affected (descriptive ranking from the EDA notebook, Chart 8; not shown in the dashboard).
- Reported deaths over 2020-2022 were highest in Brazil (3,296 per million) and the United States (3,174), and lowest in China (31) and Rwanda (107); the deadliest month ranged from November 2020 (France) to December 2022 (China), so the waves were not synchronized across countries.
- Reported figures depend on testing and registration, so low values in some countries do not prove a milder epidemic.

### Government response
- 6 of 7 countries reached their strictest month during 2020 (Germany in January 2021); the highest monthly stringency recorded was 98.6 (India, April 2020).
- Restrictions eased between 2020 and 2022 in 6 countries and rose only in China (average stringency 68.3 to 77.6).
- The largest gap between the rules for non-vaccinated and vaccinated people was 45.4 points in France (September 2021), followed by Rwanda (44.5, October 2022); China recorded no gap.

### Linking health, policy and the economy
- The economic loss did not follow the death toll: in 2020, Rwanda and India had the largest losses with 6 and 104 reported deaths per million, against 975 in France and 1,009 in the United States (rank correlation +0.07, n = 7). The dashboard shows this on the Country Comparisons page and in the "within each single year" table of the Pandemic & Policy Response page (Links with the economy tab).
- Across 2020-2022 (21 country-years), the dashboard runs 9 pooled Spearman tests (deaths, cases and stringency against the GDP, unemployment and inflation differences). One has an unadjusted p-value below 0.05: restriction strictness vs the inflation difference (rho -0.51, p = 0.019). None remains below 0.05 after a Bonferroni correction for 9 tests. (The notebook ran 6 of these 9 tests and found the same single result.)
- That pooled association is a timing effect, not a stable link between countries: within single years the correlation is +0.86 (2020), -0.32 (2021) and -0.32 (2022). Restrictions eased in 2022, the same year inflation peaked. It does not indicate cause.

## Theme 5. Economic recovery
- All 7 economies were above their 2019 size by 2022; France and Germany were still below it in 2021, and China never fell below it.
- By 2024, 6 of 7 economies remained below the estimated 2018-2019 growth trend, the largest shortfall being Rwanda (-11%); Brazil was above it (+3%). The trend is a simple extension of 2018-2019 growth, so countries with fast pre-COVID growth get a demanding benchmark.
- Unemployment returned to its 2019 level at some point by 2024 in 6 of 7 countries (all except Rwanda), and inflation was below 3% in 2024 in China, France, Germany, Rwanda and the United States.

## Country summary table

*Each economic measure is compared with the country's own 2018-2019 average or trend; countries are sorted from most to least affected on average. The average impact rank comes from the EDA notebook and weights the four measures equally, which is a team choice rather than a standard index.*

| Country | GDP vs own normal, 2020 (pts) | Unemployment change 2019-20 (pts) | Inflation vs own normal, 2022 (pts) | Economy vs trend, 2024 (%) | Reported deaths per million, 2020-22 | Average stringency (0-100) | Average impact rank (1 = hardest hit) |
|---|---|---|---|---|---|---|---|
| Rwanda | -11.5 | +0.6 | +16.2 | -11.1 | 107 | 53.8 | 2.0 |
| United States | -4.9 | +4.4 | +5.9 | -1.7 | 3,174 | 48.4 | 3.2 |
| Germany | -5.2 | +0.7 | +5.3 | -5.1 | 1,971 | 44.1 | 3.8 |
| India | -10.9 | +1.3 | +2.9 | -0.7 | 372 | 57.9 | 4.2 |
| Brazil | -4.8 | +1.8 | +5.6 | +3.4 | 3,296 | 48.5 | 4.5 |
| France | -9.3 | -0.4 | +3.7 | -4.8 | 2,515 | 42.3 | 4.8 |
| China | -4.1 | +0.4 | -0.5 | -7.1 | 31 | 73.3 | 5.5 |

## Limits
- Seven selected countries, not the world; health and policy data cover 2020-2022 only (21 country-years).
- The pre-COVID baseline and trend are estimates based on two years (2018-2019), so one unusual year changes them.
- Reported cases and deaths are not fully comparable across countries.
- Pooled correlations mix differences between years with differences between countries, and several tests are run at once.
- Associations do not establish cause.
