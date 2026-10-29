import unittest
from results import FIELDS, IDENTITY, summarize, validate


class ResultValidation(unittest.TestCase):
    def metadata(self):
        meta = dict.fromkeys(IDENTITY, 'recorded-test-identity')
        return meta | dict(fpu_mode='hardware_fp64', run_id='test-run', dataset_sha='test-dataset',
                           timer='std::time::Instant',
                           algorithm_revisions={'Baseline': 'upstream-sha', 'Candidate': 'candidate-sha'})

    def raw(self):
        return [dict(implementation=kind, test_distribution='positive', mode='throughput',
                     round=str(round_id), ticks=str(ticks), timer_hz='1000000000',
                     calls='1000', checksum='1')
                for round_id in range(15) for kind, ticks in [('Baseline', 3000), ('Candidate', 1000)]]

    def test_paired_speedup_and_unknown_cycles(self):
        rows = summarize(self.raw(), self.metadata())
        candidate = next(r for r in rows if r['implementation'] == 'Candidate')
        self.assertEqual(candidate['speedup'], 3)
        self.assertEqual(candidate['cycles_per_op'], '')
        self.assertEqual(candidate['accuracy_status'], 'NOT_TESTED')
        self.assertEqual(candidate['text_bytes'], '')

    def test_unpaired_trial_fails(self):
        with self.assertRaisesRegex(ValueError, 'unpaired'):
            summarize(self.raw()[:-1], self.metadata())

    def test_same_triple_missing_cpu_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'target_cpu'):
            summarize(self.raw(), self.metadata() | {'target_cpu': ''})

    def test_duplicate_trial_fails(self):
        raw = self.raw()
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            summarize(raw + raw[:1], self.metadata())

    def test_unknown_accuracy_cannot_pass(self):
        row = summarize(self.raw(), self.metadata())[0]
        with self.assertRaisesRegex(ValueError, 'MPFR'):
            validate(row | {'accuracy_status': 'PASS'})

    def test_blocked_is_explicit_and_has_no_zero_placeholder(self):
        row = dict.fromkeys(FIELDS, '') | dict(measurement_status='BLOCKED', accuracy_status='NOT_TESTED',
                                              reason='No board connected')
        validate(row)
        self.assertEqual(row['ns_per_op'], '')


if __name__ == '__main__':
    unittest.main()
