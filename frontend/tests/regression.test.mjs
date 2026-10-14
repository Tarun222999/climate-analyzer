import assert from 'node:assert/strict'
import test from 'node:test'
import { describeRegression, historicalTrendValues } from '../src/utils/regression.ts'

function available(change = 2.1) {
  return {
    metric: 'events_starting_in_selection',
    minimum_complete_years: 10,
    status: 'available',
    reason: null,
    years_used: Array.from({ length: 10 }, (_, index) => 2000 + index),
    slope_events_per_year: change / 10,
    change_per_decade: change,
    fitted_values: [],
  }
}

test('aligns fitted values by year, preserves zero/negative/fractional values and excluded-year gaps', () => {
  const result = {
    annual: [1999, 2000, 2001, 2002, 2003, 2004].map((year) => ({ year })),
    regression: {
      ...available(),
      fitted_values: [
        { year: 2003, fitted_event_starts: 0.123456789 },
        { year: 2000, fitted_event_starts: -0.75 },
        { year: 2002, fitted_event_starts: 0 },
      ],
    },
  }
  assert.deepEqual(historicalTrendValues(result), [null, -0.75, null, 0, 0.123456789, null])
})

test('unavailable fit explains minimum and does not invent fitted zeroes', () => {
  const regression = {
    ...available(),
    status: 'unavailable',
    reason: 'insufficient_complete_years',
    years_used: [2020],
    slope_events_per_year: null,
    change_per_decade: null,
  }
  assert.deepEqual(historicalTrendValues({ annual: [{ year: 2020 }], regression }), [null])
  assert.match(describeRegression(regression, 2020, 2020), /at least 10 complete years/)
  assert.match(describeRegression(regression, 2020, 2020), /Using 1 complete year within/)
})

test('increasing and decreasing descriptions use positive magnitudes and correct direction', () => {
  assert.match(describeRegression(available(2.1), 2000, 2009), /rose by an estimated 2.1 events per decade/)
  const falling = describeRegression(available(-2.1), 2000, 2009)
  assert.match(falling, /fell by an estimated 2.1 events per decade/)
  assert.doesNotMatch(falling, /-2.1/)
})

test('constant fit is available and described as no fitted change', () => {
  assert.match(describeRegression(available(0), 2000, 2009), /no change.*0.0 events per decade/)
  assert.doesNotMatch(describeRegression(available(0), 2000, 2009), /unavailable/)
})

test('near-zero changes retain direction without reporting a contradictory zero magnitude', () => {
  assert.match(describeRegression(available(0.001), 2000, 2009), /rose by less than 0.1/)
  assert.match(describeRegression(available(-0.001), 2000, 2009), /fell by less than 0.1/)
})

test('description uses actual included-year count and selected period even with gaps', () => {
  const regression = available()
  regression.years_used = [2000, 2001, 2003, 2005, 2007, 2009, 2011, 2013, 2015, 2018]
  assert.match(describeRegression(regression, 1999, 2020), /Using 10 complete years within the selected 1999–2020 period/)
})
