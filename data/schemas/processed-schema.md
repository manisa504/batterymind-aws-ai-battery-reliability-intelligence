# Processed measurement schema

All timestamps reproduce NASA MATLAB date vectors without assigning a timezone.

## cycles.parquet

One row per source operation: `battery_id`, zero-based `source_cycle_index`, operation `type`,
`ambient_temperature_c`, `experiment_started_at_local`, optional `discharge_cycle_index`, optional
`capacity_ah`, `sample_count`, `source_file_sha256`, and `quality_flags`.

## samples.parquet

One row per time sample: battery and source-cycle keys, `sample_index`, `elapsed_seconds`, measured
voltage/current/temperature, load/charger voltage/current, and source-file hash. Fields unavailable
for an operation remain null; they are never filled with synthetic values.

## impedance.parquet

One row per impedance sample: source keys, `sample_index`, complex-valued fields split into real and
imaginary components, plus available `re_ohm` and `rct_ohm` values.

