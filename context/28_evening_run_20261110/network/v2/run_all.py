#!/usr/bin/env python3
"""Deterministic offline calculation and verification from pinned local inputs."""
import contextlib
import io
import calculate
import calendars
import package_data
import extract_evidence
import subsidy_addendum
import evidence38f_addendum
import finalize
import verify


if __name__=='__main__':
    with contextlib.redirect_stdout(io.StringIO()):
        calculate.main()
    calendars.main()
    package_data.main()
    extract_evidence.main()
    subsidy_addendum.main()
    evidence38f_addendum.main()
    finalize.findings()
    verify.main()
    finalize.manifest()
    print('one network package built; first slice unchanged; no network calls or annualisation')
